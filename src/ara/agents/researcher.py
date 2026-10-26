"""Bounded evidence retrieval through the ARA MCP client."""

from __future__ import annotations

import asyncio
import math
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, Literal, Protocol
from urllib.parse import urlsplit

from mcp.types import CallToolResult
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictFloat,
    StrictStr,
    ValidationError,
    field_validator,
)

from ara.agents.prompts.researcher import (
    assistant_tool_call_message,
    observation_messages,
    researcher_messages,
)
from ara.agents.state import AgentState, EvidenceItem, PlanTask
from ara.agents.trace import TraceEvent, TraceScalar, make_trace_event
from ara.llm.client import ChatMessage, OllamaClient, ToolCall

_MAX_QUERY_LENGTH = 2_000
_MAX_URL_LENGTH = 2_048
_MAX_OBSERVATION_TEXT = 1_200
_MAX_EVIDENCE_TEXT = 20_000

TOOL_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Search ARA's indexed local documents for relevant evidence.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "minLength": 1}},
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the public web and return citation-ready snippets and URLs.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "minLength": 1}},
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_page",
            "description": "Fetch one public HTTP(S) page as bounded, sanitized text.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "minLength": 1}},
                "required": ["url"],
                "additionalProperties": False,
            },
        },
    },
)


class ResearcherError(RuntimeError):
    """Raised when a model tool call or MCP result violates the researcher contract."""


class ToolCallingClient(Protocol):
    """Small interface implemented by OllamaClient and deterministic test doubles."""

    def tool_calls(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[Mapping[str, Any]],
        *,
        temperature: float | None = None,
    ) -> list[ToolCall]: ...


class MCPToolClient(Protocol):
    """The MCP client operations used by the researcher."""

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Mapping[str, object],
        *,
        timeout_seconds: float | None = None,
        retries: int | None = None,
    ) -> CallToolResult: ...


class QueryArguments(BaseModel):
    """Strict query arguments for retrieval tools."""

    model_config = ConfigDict(extra="forbid", strict=True)

    query: StrictStr = Field(min_length=1, max_length=_MAX_QUERY_LENGTH)

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("query must not be blank")
        return normalized


class FetchPageArguments(BaseModel):
    """Strict URL arguments for safe web page fetching."""

    model_config = ConfigDict(extra="forbid", strict=True)

    url: StrictStr = Field(min_length=1, max_length=_MAX_URL_LENGTH)

    @field_validator("url")
    @classmethod
    def validate_public_http_url_shape(cls, value: str) -> str:
        normalized = value.strip()
        parts = urlsplit(normalized)
        if (
            parts.scheme.lower() not in {"http", "https"}
            or not parts.hostname
            or parts.username is not None
            or parts.password is not None
        ):
            raise ValueError("URL must be HTTP(S), include a host, and contain no credentials")
        return normalized


class DLChunkScore(BaseModel):
    """Validated score for a previously retrieved local evidence chunk."""

    model_config = ConfigDict(extra="forbid", strict=True)

    chunk_id: StrictStr = Field(min_length=1, max_length=128)
    relevance_score: StrictFloat
    credibility_score: StrictFloat | None = None

    @field_validator("relevance_score", "credibility_score")
    @classmethod
    def validate_probability(cls, value: float | None) -> float | None:
        if value is not None and (not math.isfinite(value) or not 0 <= value <= 1):
            raise ValueError("score must be a finite probability between zero and one")
        return value


class DLScoreResponse(BaseModel):
    """Strict envelope returned by the optional DL MCP server."""

    model_config = ConfigDict(extra="forbid", strict=True)

    status: Literal["ready", "not_ready"]
    scores: list[DLChunkScore]
    message: StrictStr | None = None


class WebSearchResultPayload(BaseModel):
    """Validated untrusted search result used to choose a page URL."""

    model_config = ConfigDict(extra="forbid", strict=True)

    chunk_id: StrictStr = Field(min_length=1, max_length=128)
    title: StrictStr = Field(min_length=1, max_length=300)
    url: StrictStr = Field(min_length=1, max_length=_MAX_URL_LENGTH)
    snippet: StrictStr = Field(max_length=1_000)
    is_untrusted: Literal[True]


class ResearchSummary(BaseModel):
    """Bounded summary of one research pass; evidence itself remains in AgentState."""

    model_config = ConfigDict(extra="forbid")

    tool_calls_made: int = Field(ge=0)
    evidence_ids_added: list[str] = Field(default_factory=list)
    completed_task_ids: list[str] = Field(default_factory=list)
    blocked_task_ids: list[str] = Field(default_factory=list)
    tool_budget_exhausted: bool = False
    evidence_budget_exhausted: bool = False


class _ValidatedCall(BaseModel):
    """A known tool mapped to its connected MCP server and safe arguments."""

    model_config = ConfigDict(extra="forbid")

    server_name: str
    tool_name: str
    arguments: dict[str, object]


class Researcher:
    """Research plan tasks with LLM-selected calls to named MCP servers.

    The MCP client must already have `rag` and `web` servers connected. When
    enabled, local search results are reranked through the optional `dl-model`
    server. Every invocation is made once with retries disabled, so the call
    budget bounds MCP invocations as well as model-selected actions.
    """

    def __init__(
        self,
        mcp_client: MCPToolClient,
        llm_client: ToolCallingClient | None = None,
        *,
        max_tool_calls: int = 24,
        max_evidence_items: int = 100,
        max_evidence_chars: int = 500_000,
        local_top_k: int = 5,
        web_max_results: int = 5,
        mcp_timeout_seconds: float = 20.0,
        use_dl_scorer: bool | None = None,
    ) -> None:
        self._mcp = mcp_client
        self._llm = llm_client if llm_client is not None else OllamaClient()
        self.max_tool_calls = _positive_int(max_tool_calls, "max_tool_calls", maximum=200)
        self.max_evidence_items = _positive_int(
            max_evidence_items,
            "max_evidence_items",
            maximum=10_000,
        )
        self.max_evidence_chars = _positive_int(
            max_evidence_chars,
            "max_evidence_chars",
            maximum=20_000_000,
        )
        self.local_top_k = _positive_int(local_top_k, "local_top_k", maximum=50)
        self.web_max_results = _positive_int(web_max_results, "web_max_results", maximum=10)
        if use_dl_scorer is None:
            from ara.config import load_settings

            use_dl_scorer = load_settings().dl_use_scorer
        if not isinstance(use_dl_scorer, bool):
            raise ValueError("use_dl_scorer must be a boolean")
        self.use_dl_scorer = use_dl_scorer
        if (
            isinstance(mcp_timeout_seconds, bool)
            or not isinstance(mcp_timeout_seconds, (int, float))
            or not math.isfinite(mcp_timeout_seconds)
            or mcp_timeout_seconds <= 0
        ):
            raise ValueError("mcp_timeout_seconds must be finite and positive")
        self.mcp_timeout_seconds = float(mcp_timeout_seconds)

    async def research(
        self,
        state: AgentState,
        *,
        trace_callback: Callable[[TraceEvent], None] | None = None,
    ) -> ResearchSummary:
        """Execute eligible plan tasks, adding bounded citation-ready evidence."""
        ordered_tasks = _topological_tasks(state.plan)
        tool_calls_made = 0
        evidence_ids_added: list[str] = []
        completed_task_ids: list[str] = []
        budget_blocking = False
        tool_budget_exhausted = False
        evidence_budget_exhausted = False

        try:
            for position, task in enumerate(ordered_tasks):
                if task.status in {"completed", "blocked"}:
                    continue
                if any(
                    _find_task(state.plan, dependency).status != "completed"
                    for dependency in task.depends_on
                ):
                    task.status = "blocked"
                    _emit_trace(
                        trace_callback,
                        state,
                        event="task_blocked",
                        task_id=task.task_id,
                        result_summary="a prerequisite task is not completed",
                    )
                    continue
                if budget_blocking:
                    task.status = "blocked"
                    _emit_trace(
                        trace_callback,
                        state,
                        event="task_blocked",
                        task_id=task.task_id,
                        result_summary="a research budget was exhausted",
                    )
                    continue

                task.status = "in_progress"
                task_tool_calls_start = tool_calls_made
                task_evidence_start = len(evidence_ids_added)
                task_had_web_search = False
                task_had_local_search = False
                forced_fallback_calls: list[ToolCall] | None = None
                _emit_trace(
                    trace_callback,
                    state,
                    event="task_started",
                    task_id=task.task_id,
                )
                messages = researcher_messages(state.topic, task)
                try:
                    while True:
                        fallback_selected = forced_fallback_calls is not None
                        if forced_fallback_calls is not None:
                            calls = forced_fallback_calls
                            forced_fallback_calls = None
                        else:
                            calls = await asyncio.to_thread(
                                self._llm.tool_calls,
                                messages,
                                TOOL_DEFINITIONS,
                                temperature=0.0,
                            )
                        if not calls:
                            needs_local_fallback = (
                                task_had_web_search
                                and not task_had_local_search
                                and len(evidence_ids_added) == task_evidence_start
                            )
                            if needs_local_fallback and tool_calls_made < self.max_tool_calls:
                                calls = [
                                    ToolCall(
                                        name="search_knowledge_base",
                                        arguments={"query": task.question},
                                    )
                                ]
                                fallback_selected = True
                            else:
                                task.status = "completed"
                                completed_task_ids.append(task.task_id)
                                _emit_trace(
                                    trace_callback,
                                    state,
                                    event="task_completed",
                                    task_id=task.task_id,
                                    result_summary=(
                                        f"tool_calls={tool_calls_made - task_tool_calls_start}; "
                                        f"evidence_added="
                                        f"{len(evidence_ids_added) - task_evidence_start}"
                                    ),
                                )
                                break

                        for call in calls:
                            _emit_trace(
                                trace_callback,
                                state,
                                event="tool_selected",
                                task_id=task.task_id,
                                tool_name=call.name,
                                tool_arguments=_trace_arguments(call.arguments),
                                result_summary=(
                                    "selected_by=local_evidence_fallback; "
                                    "reason=web_search_added_no_evidence"
                                    if fallback_selected
                                    else None
                                ),
                            )
                        validated_calls = [
                            _validate_tool_call(
                                call,
                                local_top_k=self.local_top_k,
                                web_max_results=self.web_max_results,
                            )
                            for call in calls
                        ]
                        observations: list[dict[str, object]] = []
                        for validated_call in validated_calls:
                            if tool_calls_made >= self.max_tool_calls:
                                tool_budget_exhausted = True
                                budget_blocking = True
                                break
                            if validated_call.tool_name == "web_search":
                                task_had_web_search = True
                            elif validated_call.tool_name == "search_knowledge_base":
                                task_had_local_search = True
                            tool_calls_made += 1
                            call_started = time.perf_counter()
                            try:
                                result = await self._mcp.call_tool(
                                    validated_call.server_name,
                                    validated_call.tool_name,
                                    validated_call.arguments,
                                    timeout_seconds=self.mcp_timeout_seconds,
                                    retries=0,
                                )
                                response = _structured_response(result, validated_call.tool_name)
                                candidates = _evidence_from_result(
                                    validated_call.tool_name,
                                    response,
                                    local_top_k=self.local_top_k,
                                    web_max_results=self.web_max_results,
                                )
                                if (
                                    self.use_dl_scorer
                                    and validated_call.tool_name == "search_knowledge_base"
                                    and candidates
                                ):
                                    if tool_calls_made < self.max_tool_calls:
                                        query = validated_call.arguments["query"]
                                        if not isinstance(query, str):
                                            raise ResearcherError(
                                                "validated local query was not text"
                                            )
                                        score_ids = [item.chunk_id for item in candidates]
                                        score_arguments = {
                                            "query": query,
                                            "chunk_ids": score_ids,
                                        }
                                        tool_calls_made += 1
                                        score_started = time.perf_counter()
                                        score_summary = "status=fallback; error_type=unknown"
                                        try:
                                            score_result = await self._mcp.call_tool(
                                                "dl-model",
                                                "score_chunks",
                                                score_arguments,
                                                timeout_seconds=self.mcp_timeout_seconds,
                                                retries=0,
                                            )
                                            if score_result.is_error:
                                                score_summary = (
                                                    "status=fallback; reason=mcp_error"
                                                )
                                            elif not isinstance(
                                                score_result.structured_content, Mapping
                                            ):
                                                score_summary = (
                                                    "status=fallback; reason=missing_response"
                                                )
                                            else:
                                                score_payload = DLScoreResponse.model_validate(
                                                    score_result.structured_content
                                                )
                                                if score_payload.status == "not_ready":
                                                    score_summary = (
                                                        "status=not_ready; fallback=true"
                                                    )
                                                else:
                                                    candidates, response = _apply_dl_scores(
                                                        candidates,
                                                        response,
                                                        score_payload,
                                                    )
                                                    scored_count = len(score_payload.scores)
                                                    score_summary = (
                                                        f"status=ready; scored={scored_count}; "
                                                        "evidence_reordered=true"
                                                    )
                                        except Exception as exc:
                                            score_summary = (
                                                "status=fallback; "
                                                f"error_type={type(exc).__name__}"
                                            )
                                        _emit_trace(
                                            trace_callback,
                                            state,
                                            event="tool_call",
                                            task_id=task.task_id,
                                            tool_name="score_chunks",
                                            server_name="dl-model",
                                            tool_arguments=_trace_arguments(
                                                {
                                                    "query": query,
                                                    "chunk_ids": ",".join(score_ids),
                                                    "candidate_count": len(score_ids),
                                                }
                                            ),
                                            result_summary=score_summary,
                                            latency_ms=(time.perf_counter() - score_started)
                                            * 1_000,
                                            is_untrusted=True,
                                        )
                                    else:
                                        _emit_trace(
                                            trace_callback,
                                            state,
                                            event="scorer_skipped",
                                            task_id=task.task_id,
                                            server_name="dl-model",
                                            result_summary="tool_budget_limit",
                                        )
                                added, evidence_limit_hit = _add_evidence(
                                    state,
                                    candidates,
                                    max_items=self.max_evidence_items,
                                    max_chars=self.max_evidence_chars,
                                )
                            except Exception as exc:
                                _emit_trace(
                                    trace_callback,
                                    state,
                                    event="tool_call",
                                    task_id=task.task_id,
                                    tool_name=validated_call.tool_name,
                                    server_name=validated_call.server_name,
                                    tool_arguments=_trace_arguments(validated_call.arguments),
                                    result_summary=f"error_type={type(exc).__name__}",
                                    latency_ms=(time.perf_counter() - call_started) * 1_000,
                                )
                                raise
                            evidence_ids_added.extend(added)
                            evidence_budget_exhausted = (
                                evidence_budget_exhausted or evidence_limit_hit
                            )
                            if evidence_limit_hit:
                                budget_blocking = True
                            _emit_trace(
                                trace_callback,
                                state,
                                event="tool_call",
                                task_id=task.task_id,
                                tool_name=validated_call.tool_name,
                                server_name=validated_call.server_name,
                                tool_arguments=_trace_arguments(validated_call.arguments),
                                result_summary=(
                                    f"results={_result_count(validated_call.tool_name, response)}; "
                                    f"evidence_added={len(added)}; "
                                    f"new_ids={','.join(added[:5])}; "
                                    f"additional_ids={max(0, len(added) - 5)}; "
                                    f"evidence_budget_hit={evidence_limit_hit}"
                                ),
                                latency_ms=(time.perf_counter() - call_started) * 1_000,
                                is_untrusted=True,
                            )
                            observations.append(
                                _observation(
                                    validated_call.tool_name,
                                    response,
                                    self.local_top_k,
                                    self.web_max_results,
                                )
                            )
                            if budget_blocking:
                                break

                        if budget_blocking:
                            task.status = "blocked"
                            _emit_trace(
                                trace_callback,
                                state,
                                event="task_blocked",
                                task_id=task.task_id,
                                result_summary="a research budget was exhausted",
                            )
                            break
                        messages.append(assistant_tool_call_message(calls))
                        messages.extend(observation_messages(observations))
                        if fallback_selected:
                            task.status = "completed"
                            completed_task_ids.append(task.task_id)
                            _emit_trace(
                                trace_callback,
                                state,
                                event="task_completed",
                                task_id=task.task_id,
                                result_summary=(
                                    f"tool_calls={tool_calls_made - task_tool_calls_start}; "
                                    f"evidence_added="
                                    f"{len(evidence_ids_added) - task_evidence_start}; "
                                    "completion=local_fallback"
                                ),
                            )
                            break
                        if (
                            task_had_web_search
                            and not task_had_local_search
                            and len(evidence_ids_added) == task_evidence_start
                            and state.evidence_store
                            and tool_calls_made < self.max_tool_calls
                        ):
                            forced_fallback_calls = [
                                ToolCall(
                                    name="search_knowledge_base",
                                    arguments={"query": task.question},
                                )
                            ]
                except Exception:
                    task.status = "blocked"
                    _emit_trace(
                        trace_callback,
                        state,
                        event="task_failed",
                        task_id=task.task_id,
                        result_summary="research operation raised an exception",
                    )
                    raise

                if budget_blocking:
                    for remaining in ordered_tasks[position + 1 :]:
                        if remaining.status in {"pending", "in_progress"}:
                            remaining.status = "blocked"
                            _emit_trace(
                                trace_callback,
                                state,
                                event="task_blocked",
                                task_id=remaining.task_id,
                                result_summary="a research budget was exhausted",
                            )
                    break
        finally:
            state.run_metadata.updated_at = datetime.now(UTC)

        return ResearchSummary(
            tool_calls_made=tool_calls_made,
            evidence_ids_added=evidence_ids_added,
            completed_task_ids=completed_task_ids,
            blocked_task_ids=[task.task_id for task in ordered_tasks if task.status == "blocked"],
            tool_budget_exhausted=tool_budget_exhausted,
            evidence_budget_exhausted=evidence_budget_exhausted,
        )


def _positive_int(value: int, name: str, *, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise ValueError(f"{name} must be between 1 and {maximum}")
    return value


def _topological_tasks(tasks: Sequence[PlanTask]) -> list[PlanTask]:
    """Return tasks with dependencies first, preserving order where possible."""
    remaining = list(tasks)
    ordered: list[PlanTask] = []
    emitted: set[str] = set()
    known = {task.task_id for task in tasks}
    if any(dependency not in known for task in tasks for dependency in task.depends_on):
        raise ResearcherError("plan dependencies must reference tasks in the same plan")
    while remaining:
        ready = [task for task in remaining if set(task.depends_on) <= emitted]
        if not ready:
            raise ResearcherError("plan dependencies must not contain cycles")
        for task in ready:
            ordered.append(task)
            emitted.add(task.task_id)
        ready_ids = {task.task_id for task in ready}
        remaining = [task for task in remaining if task.task_id not in ready_ids]
    return ordered


def _find_task(tasks: Sequence[PlanTask], task_id: str) -> PlanTask:
    for task in tasks:
        if task.task_id == task_id:
            return task
    raise ResearcherError("plan dependencies must reference tasks in the same plan")


def _validate_tool_call(
    call: ToolCall,
    *,
    local_top_k: int,
    web_max_results: int,
) -> _ValidatedCall:
    try:
        if call.name == "search_knowledge_base":
            arguments = QueryArguments.model_validate(call.arguments)
            return _ValidatedCall(
                server_name="rag",
                tool_name=call.name,
                arguments={
                    "query": arguments.query,
                    "top_k": local_top_k,
                    "candidate_k": min(local_top_k * 4, 200),
                },
            )
        if call.name == "web_search":
            arguments = QueryArguments.model_validate(call.arguments)
            return _ValidatedCall(
                server_name="web",
                tool_name=call.name,
                arguments={"query": arguments.query, "max_results": web_max_results},
            )
        if call.name == "fetch_page":
            page_arguments = FetchPageArguments.model_validate(call.arguments)
            return _ValidatedCall(
                server_name="web",
                tool_name=call.name,
                arguments={"url": page_arguments.url},
            )
    except ValidationError as exc:
        raise ResearcherError(f"model provided invalid arguments for {call.name!r}") from exc
    raise ResearcherError(f"model requested a disallowed research tool: {call.name!r}")


def _structured_response(result: CallToolResult, tool_name: str) -> Mapping[str, Any]:
    if result.is_error:
        raise ResearcherError(f"MCP tool {tool_name!r} returned an error")
    if not isinstance(result.structured_content, Mapping):
        raise ResearcherError(f"MCP tool {tool_name!r} returned no structured content")
    return result.structured_content


def _evidence_from_result(
    tool_name: str,
    response: Mapping[str, Any],
    *,
    local_top_k: int,
    web_max_results: int,
) -> list[EvidenceItem]:
    if tool_name == "search_knowledge_base":
        records = response.get("results")
        if not isinstance(records, list):
            raise ResearcherError("local search result did not contain a results list")
        return [_local_evidence(record) for record in records[:local_top_k]]
    if tool_name == "web_search":
        # Search IDs also identify fetched pages; snippets guide URL selection but
        # are not citation evidence because the page will reuse the same stable ID.
        _validated_web_search_results(response, max_results=web_max_results)
        return []
    if tool_name == "fetch_page":
        try:
            item = EvidenceItem.model_validate(
                {
                    "chunk_id": response.get("chunk_id"),
                    "text": response.get("content"),
                    "source": response.get("title"),
                    "source_type": "web",
                    "url": response.get("url"),
                    "is_untrusted": True,
                }
            )
        except ValidationError as exc:
            raise ResearcherError("fetched page result did not match the evidence schema") from exc
        return [item]
    raise ResearcherError(f"no evidence conversion is defined for tool {tool_name!r}")


def _apply_dl_scores(
    candidates: Sequence[EvidenceItem],
    response: Mapping[str, Any],
    payload: DLScoreResponse,
) -> tuple[list[EvidenceItem], Mapping[str, Any]]:
    """Rank only the exact local candidates returned by the retrieval tool."""
    score_by_id = {score.chunk_id: score.relevance_score for score in payload.scores}
    candidate_ids = [candidate.chunk_id for candidate in candidates]
    if len(score_by_id) != len(payload.scores) or set(score_by_id) != set(candidate_ids):
        raise ResearcherError("DL scorer returned missing, duplicate, or unknown chunk IDs")

    ranked_candidates = sorted(
        candidates,
        key=lambda candidate: -score_by_id[candidate.chunk_id],
    )
    raw_records = response.get("results")
    if not isinstance(raw_records, list):
        raise ResearcherError("local search result did not contain a results list")
    candidate_id_set = set(candidate_ids)
    record_by_id = {
        record.get("chunk_id"): record
        for record in raw_records
        if isinstance(record, Mapping)
        and isinstance(record.get("chunk_id"), str)
        and record.get("chunk_id") in candidate_id_set
    }
    if set(record_by_id) != set(candidate_ids):
        raise ResearcherError("local search result IDs changed before DL reranking")
    ranked_response = {
        **response,
        "results": [record_by_id[item.chunk_id] for item in ranked_candidates],
    }
    return ranked_candidates, ranked_response


def _local_evidence(record: object) -> EvidenceItem:
    if not isinstance(record, Mapping):
        raise ResearcherError("local search returned a malformed result")
    if not isinstance(record.get("text"), str) or not isinstance(record.get("source"), str):
        raise ResearcherError("local search result did not contain text and source strings")
    try:
        return EvidenceItem.model_validate(
            {
                "chunk_id": record.get("chunk_id"),
                "text": record.get("text", "")[:_MAX_EVIDENCE_TEXT],
                "source": record.get("source"),
                "source_type": "local",
                "page": record.get("page"),
                "score": record.get("score"),
                "is_untrusted": True,
            }
        )
    except ValidationError as exc:
        raise ResearcherError("local search result did not match the evidence schema") from exc


def _add_evidence(
    state: AgentState,
    candidates: Sequence[EvidenceItem],
    *,
    max_items: int,
    max_chars: int,
) -> tuple[list[str], bool]:
    existing_chars = sum(len(item.text) for item in state.evidence_store.values())
    remaining_items = max_items - len(state.evidence_store)
    remaining_chars = max_chars - existing_chars
    seen_ids = set(state.evidence_store)
    prepared: list[EvidenceItem] = []
    budget_hit = False
    for item in candidates:
        if item.chunk_id in seen_ids:
            prepared.append(item)
            continue
        if remaining_items <= 0 or remaining_chars <= 0:
            budget_hit = True
            break
        text = item.text[: min(len(item.text), remaining_chars, _MAX_EVIDENCE_TEXT)]
        if not text:
            budget_hit = True
            break
        if len(text) < len(item.text):
            budget_hit = True
        prepared.append(item.model_copy(update={"text": text}))
        seen_ids.add(item.chunk_id)
        remaining_items -= 1
        remaining_chars -= len(text)
    try:
        added = state.add_evidence_many(prepared)
    except ValueError as exc:
        raise ResearcherError("retrieval reused an evidence ID for different content") from exc
    return added, budget_hit


def _observation(
    tool_name: str,
    response: Mapping[str, Any],
    local_top_k: int,
    web_max_results: int,
) -> dict[str, object]:
    if tool_name == "search_knowledge_base":
        raw_records = response.get("results", [])
        entries = raw_records[:local_top_k] if isinstance(raw_records, list) else []
        results = [
            {
                "chunk_id": record.get("chunk_id"),
                "source": record.get("source"),
                "page": record.get("page"),
                "excerpt": str(record.get("text", ""))[:_MAX_OBSERVATION_TEXT],
            }
            for record in entries
            if isinstance(record, Mapping)
        ]
    elif tool_name == "web_search":
        results = [
            {
                "chunk_id": record.chunk_id,
                "title": record.title,
                "url": record.url,
                "snippet": record.snippet[:_MAX_OBSERVATION_TEXT],
                "is_untrusted": True,
            }
            for record in _validated_web_search_results(
                response,
                max_results=web_max_results,
            )
        ]
    elif tool_name == "fetch_page":
        results = [
            {
                "chunk_id": response.get("chunk_id"),
                "title": response.get("title"),
                "url": response.get("url"),
                "excerpt": str(response.get("content", ""))[:_MAX_OBSERVATION_TEXT],
                "is_untrusted": True,
            }
        ]
    else:
        raise ResearcherError(f"no observation formatter is defined for tool {tool_name!r}")
    return {"tool": tool_name, "results": results, "is_untrusted": True}


def _validated_web_search_results(
    response: Mapping[str, Any],
    *,
    max_results: int,
) -> list[WebSearchResultPayload]:
    records = response.get("results")
    if not isinstance(records, list):
        raise ResearcherError("web search result did not contain a results list")
    validated: list[WebSearchResultPayload] = []
    for record in records[:max_results]:
        try:
            parsed = WebSearchResultPayload.model_validate(record)
            FetchPageArguments(url=parsed.url)
        except (ValidationError, TypeError) as exc:
            raise ResearcherError("web search returned a malformed result") from exc
        if not parsed.chunk_id.startswith("web:"):
            raise ResearcherError("web search returned an invalid citation ID")
        validated.append(parsed)
    return validated


def _result_count(tool_name: str, response: Mapping[str, Any]) -> int:
    if tool_name in {"search_knowledge_base", "web_search"}:
        results = response.get("results")
        return len(results) if isinstance(results, list) else 0
    if tool_name == "fetch_page":
        return 1 if isinstance(response.get("content"), str) and response["content"].strip() else 0
    return 0


def _trace_arguments(arguments: Mapping[str, object]) -> dict[str, TraceScalar]:
    bounded: dict[str, TraceScalar] = {}
    for name, value in arguments.items():
        if isinstance(value, str):
            bounded[name] = value[:500]
        elif value is None or isinstance(value, (bool, int, float)):
            bounded[name] = value
    return bounded


def _emit_trace(
    callback: Callable[[TraceEvent], None] | None,
    state: AgentState,
    *,
    event: str,
    task_id: str | None = None,
    tool_name: str | None = None,
    server_name: str | None = None,
    tool_arguments: Mapping[str, TraceScalar] | None = None,
    result_summary: str | None = None,
    latency_ms: float | None = None,
    is_untrusted: bool | None = None,
) -> None:
    if callback is None:
        return
    callback(
        make_trace_event(
            state.run_metadata.run_id,
            agent="researcher",
            event=event,
            task_id=task_id,
            tool_name=tool_name,
            server_name=server_name,
            tool_arguments=tool_arguments,
            result_summary=result_summary,
            latency_ms=latency_ms,
            is_untrusted=is_untrusted,
        )
    )


__all__ = [
    "MCPToolClient",
    "Researcher",
    "ResearcherError",
    "ResearchSummary",
    "TOOL_DEFINITIONS",
    "ToolCallingClient",
]
