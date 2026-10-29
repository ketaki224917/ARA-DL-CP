"""Loopback-only browser interface for running ARA with optional local documents."""

from __future__ import annotations

import argparse
import ipaddress
import json
import logging
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import threading
import uuid
import webbrowser
from collections import deque
from dataclasses import dataclass, field
from email import policy
from email.parser import BytesParser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any
from urllib.parse import unquote, urlsplit

logger = logging.getLogger("ara.web")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".md", ".markdown", ".txt", ".html", ".htm"}
MAX_REQUEST_BYTES = 55 * 1024 * 1024
MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_TOTAL_FILE_BYTES = 50 * 1024 * 1024
MAX_FILES = 20
MAX_TOPIC_CHARS = 2_000
RUN_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")
ALLOWED_REPORT_FILES = {
    "report.html",
    "report.md",
    "report.pdf",
    "figures/diagram-01.svg",
    "audio/narration.wav",
}

PAGE = Path(__file__).with_name("web_app.html").read_text(encoding="utf-8")


@dataclass
class UploadedDocument:
    """Validated upload preserved as safe filename and bytes."""

    filename: str
    suffix: str
    content: bytes


@dataclass
class Job:
    """Mutable, lock-protected state for one browser-launched run."""

    session_id: str
    topic: str
    documents: list[str]
    status: str = "preparing"
    stage: str = "Preparing sources"
    logs: deque[str] = field(default_factory=lambda: deque(maxlen=180))
    output_root: Path | None = None
    report_dir: Path | None = None
    error: str | None = None


class RunManager:
    """Run ingestion and the ARA pipeline in one isolated local session."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._job: Job | None = None
        self._active = False
        self._stop_requested = False
        self._process: subprocess.Popen[str] | None = None

    def start(self, topic: str, documents: list[UploadedDocument]) -> dict[str, Any]:
        """Create a run and return its first status snapshot."""
        with self._lock:
            if self._active:
                raise RuntimeError("ARA is already running. Wait for it to finish or stop it.")
            session_id = uuid.uuid4().hex
            job = Job(
                session_id=session_id,
                topic=topic,
                documents=[document.filename for document in documents],
            )
            self._job = job
            self._active = True
            self._stop_requested = False
            worker = threading.Thread(
                target=self._work,
                args=(job, documents),
                name=f"ara-run-{session_id[:8]}",
                daemon=True,
            )
            worker.start()
            return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        """Return JSON-safe current job status."""
        with self._lock:
            job = self._job
            if job is None:
                return {"status": "ready", "topic": "", "documents": [], "logs": []}
            report_url = None
            if job.report_dir is not None:
                report_url = f"/files/{job.session_id}/report.html"
            return {
                "session_id": job.session_id,
                "status": job.status,
                "stage": job.stage,
                "topic": job.topic,
                "documents": list(job.documents),
                "logs": list(job.logs),
                "report_url": report_url,
                "error": job.error,
            }

    def stop(self) -> dict[str, Any]:
        """Stop the active child process, if one is running."""
        with self._lock:
            job = self._job
            if not self._active or job is None:
                return self.snapshot()
            self._stop_requested = True
            job.status = "stopping"
            job.stage = "Stopping the current operation"
            process = self._process
        if process is not None:
            process.terminate()
        return self.snapshot()

    def report_file(self, session_id: str, relative_path: str) -> Path | None:
        """Resolve one allow-listed report artifact from a completed session."""
        if not RUN_ID_PATTERN.fullmatch(session_id):
            return None
        if relative_path not in ALLOWED_REPORT_FILES:
            return None
        with self._lock:
            job = self._job
            if job is None or job.session_id != session_id or job.output_root is None:
                return None
            if job.report_dir is None:
                return None
            report_root = job.report_dir.resolve()
        candidate = (report_root / PurePosixPath(relative_path)).resolve()
        if not candidate.is_relative_to(report_root):
            return None
        return candidate if candidate.is_file() else None

    def _work(self, job: Job, documents: list[UploadedDocument]) -> None:
        """Prepare isolated indexes, run ARA, then publish its report location."""
        try:
            session_root = Path("data/web_sessions") / job.session_id
            source_root = session_root / "sources"
            source_root.mkdir(parents=True, exist_ok=False)
            shutil.copytree(PROJECT_ROOT / "data/sample_corpus", source_root / "sample")
            upload_root = source_root / "uploaded"
            if documents:
                upload_root.mkdir()
                for index, document in enumerate(documents, start=1):
                    safe_stem = _safe_filename(Path(document.filename).stem)
                    destination = upload_root / f"{index:02d}_{safe_stem}{document.suffix}"
                    destination.write_bytes(document.content)

            output_root = Path("outputs/web_runs") / job.session_id
            job.output_root = (PROJECT_ROOT / output_root).resolve()
            environment = os.environ.copy()
            index_root = session_root / "indexes"
            environment.update(
                {
                    "ARA_VECTOR_STORE_DIR": str(index_root / "chroma"),
                    "ARA_BM25_INDEX_PATH": str(index_root / "bm25.json"),
                    "ARA_INGEST_MANIFEST_PATH": str(index_root / "manifest.json"),
                    "ARA_EMBEDDING_CACHE_PATH": str(index_root / "embeddings.sqlite3"),
                    "ARA_OUTPUT_DIR": str(output_root),
                    "ARA_TRACE_DIR": str(Path("traces/web_runs") / job.session_id),
                }
            )

            self._set_stage(job, "indexing", "Indexing sample and uploaded documents")
            ingest_source = source_root.as_posix()
            ingest_code = self._run_command(
                job,
                [
                    sys.executable,
                    "-m",
                    "ara.cli",
                    "ingest",
                    "--source",
                    ingest_source,
                ],
                environment,
            )
            if self._is_stopping():
                self._finish(job, "stopped", "Run stopped.")
                return
            if ingest_code != 0:
                raise RuntimeError("Document indexing failed. Review the run log.")

            self._set_stage(job, "researching", "Running planner, researcher, writer, and critic")
            if self._run_command(
                job,
                [sys.executable, "-m", "ara.cli", "run", "--topic", job.topic],
                environment,
            ) != 0:
                if self._is_stopping():
                    self._finish(job, "stopped", "Run stopped.")
                else:
                    raise RuntimeError("ARA research failed. Review the run log.")
                return

            reports = list(job.output_root.rglob("report.html"))
            if not reports:
                raise RuntimeError("ARA finished without producing a report bundle.")
            report_dir = reports[0].parent
            with self._lock:
                job.report_dir = report_dir
                job.status = "completed"
                job.stage = "Research complete"
                job.logs.append("\nCompleted. Report bundle is available in the links above.\n")
                self._active = False
        except Exception as exc:
            logger.exception("Browser-launched ARA run failed")
            self._finish(job, "failed", str(exc))

    def _run_command(
        self,
        job: Job,
        command: list[str],
        environment: dict[str, str],
    ) -> int:
        """Run one project command and stream its output into the browser log."""
        if self._is_stopping():
            return -1
        process = subprocess.Popen(
            command,
            cwd=PROJECT_ROOT,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        with self._lock:
            self._process = process
            should_stop = self._stop_requested
        if should_stop:
            process.terminate()
        assert process.stdout is not None
        for line in process.stdout:
            with self._lock:
                job.logs.append(line[-2_000:])
        return_code = process.wait()
        with self._lock:
            if self._process is process:
                self._process = None
        return return_code

    def _set_stage(self, job: Job, status: str, stage: str) -> None:
        with self._lock:
            job.status = status
            job.stage = stage

    def _is_stopping(self) -> bool:
        with self._lock:
            return self._stop_requested

    def _finish(self, job: Job, status: str, message: str) -> None:
        with self._lock:
            job.status = status
            job.stage = message
            job.error = message if status == "failed" else None
            job.logs.append(f"\n{message}\n")
            self._active = False
            self._process = None


def _safe_filename(value: str) -> str:
    """Reduce a user filename to safe metadata that cannot escape its folder."""
    safe = re.sub(r"[^A-Za-z0-9._ -]+", "_", value).strip(" .")
    return safe[:100] or "document"


def _parse_multipart(
    content_type: str,
    body: bytes,
) -> tuple[str, list[UploadedDocument]]:
    """Validate topic and the allow-listed multi-file upload."""
    envelope = (
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("ascii")
        + body
    )
    message = BytesParser(policy=policy.default).parsebytes(envelope)
    if not message.is_multipart():
        raise ValueError("Use the topic form and attach files with the document picker.")

    topic = ""
    documents: list[UploadedDocument] = []
    total_bytes = 0
    for part in message.iter_parts():
        field_name = part.get_param("name", header="content-disposition")
        if field_name == "topic":
            payload = part.get_payload(decode=True)
            if not isinstance(payload, bytes):
                payload = b""
            topic = payload.decode("utf-8", errors="replace").strip()
        elif field_name == "documents":
            original_name = part.get_filename()
            if not original_name:
                continue
            safe_name = PureWindowsPath(original_name.replace("/", "\\")).name
            safe_name = PurePosixPath(safe_name).name
            suffix = Path(safe_name).suffix.lower()
            if suffix not in ALLOWED_EXTENSIONS:
                raise ValueError(f"Unsupported document type: {suffix or 'no extension'}")
            content = part.get_payload(decode=True)
            if not isinstance(content, bytes):
                content = b""
            if not content:
                raise ValueError(f"{safe_name} is empty.")
            if len(content) > MAX_FILE_BYTES:
                raise ValueError(f"{safe_name} exceeds the 20 MB per-file limit.")
            total_bytes += len(content)
            if total_bytes > MAX_TOTAL_FILE_BYTES:
                raise ValueError("The combined upload exceeds the 50 MB limit.")
            if len(documents) >= MAX_FILES:
                raise ValueError("Upload no more than 20 documents at a time.")
            documents.append(UploadedDocument(safe_name, suffix, content))

    if not topic:
        raise ValueError("Enter a research topic.")
    if len(topic) > MAX_TOPIC_CHARS:
        raise ValueError("The research topic must be 2,000 characters or fewer.")
    return topic, documents


class ARARequestHandler(BaseHTTPRequestHandler):
    """Serve a local topic-and-documents form and its small JSON API."""

    server_version = "ARA-Local/1.0"

    @property
    def manager(self) -> RunManager:
        return self.server.manager  # type: ignore[attr-defined,no-any-return]

    def do_GET(self) -> None:
        """Serve the interface, job status, or one report artifact."""
        parsed = urlsplit(self.path)
        if parsed.path == "/":
            self._send(HTTPStatus.OK, PAGE.encode("utf-8"), "text/html; charset=utf-8")
        elif parsed.path == "/api/status":
            self._send_json(HTTPStatus.OK, self.manager.snapshot())
        elif parsed.path.startswith("/files/"):
            self._serve_artifact(parsed.path)
        else:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found."})

    def do_POST(self) -> None:
        """Accept a run request or stop the active child process."""
        if not self._same_origin():
            self._send_json(
                HTTPStatus.FORBIDDEN,
                {"error": "Only same-origin local requests are accepted."},
            )
            return
        if urlsplit(self.path).path == "/api/stop":
            self._send_json(HTTPStatus.OK, self.manager.stop())
            return
        if urlsplit(self.path).path != "/api/run":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid request length."})
            return
        if length < 1 or length > MAX_REQUEST_BYTES:
            self._send_json(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                {"error": "Upload limit is 50 MB total."},
            )
            return
        try:
            topic, documents = _parse_multipart(
                self.headers.get("Content-Type", ""),
                self.rfile.read(length),
            )
            result = self.manager.start(topic, documents)
        except RuntimeError as exc:
            self._send_json(HTTPStatus.CONFLICT, {"error": str(exc)})
            return
        except (UnicodeError, ValueError) as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        self._send_json(HTTPStatus.ACCEPTED, result)

    def _same_origin(self) -> bool:
        """Reject cross-site form submissions while accepting local browsers."""
        origin = self.headers.get("Origin")
        if not origin:
            return True
        try:
            parsed = urlsplit(origin)
            server = self.server
            if not isinstance(server, ThreadingHTTPServer):
                return False
            return (
                parsed.scheme == "http"
                and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
                and parsed.port == server.server_port
            )
        except ValueError:
            return False

    def _serve_artifact(self, path: str) -> None:
        """Serve only known report files belonging to the active run."""
        parts = [unquote(part) for part in path.split("/") if part]
        if len(parts) < 3:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found."})
            return
        session_id = parts[1]
        relative_path = "/".join(parts[2:])
        allowed = relative_path in ALLOWED_REPORT_FILES
        if not allowed:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found."})
            return
        candidate = self.manager.report_file(session_id, relative_path)
        if candidate is None:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found."})
            return
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        self._send(HTTPStatus.OK, candidate.read_bytes(), content_type)

    def _send_json(self, status: HTTPStatus, value: dict[str, Any]) -> None:
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")

    def _send(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format_string: str, *args: object) -> None:
        logger.info("%s - %s", self.client_address[0], format_string % args)


class ARAServer(ThreadingHTTPServer):
    """HTTP server with a single attached job manager."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, host: str, port: int) -> None:
        super().__init__((host, port), ARARequestHandler)
        self.manager = RunManager()


def main() -> int:
    """Run the local browser interface."""
    parser = argparse.ArgumentParser(description="Run ARA's local browser interface.")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="loopback address only (default: 127.0.0.1)",
    )
    parser.add_argument("--port", type=int, default=8765, help="HTTP port (default: 8765)")
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="do not open the browser automatically",
    )
    args = parser.parse_args()
    try:
        address = ipaddress.ip_address(args.host)
    except ValueError as exc:
        raise SystemExit("--host must be a loopback IP address.") from exc
    if not address.is_loopback:
        raise SystemExit("--host must be a loopback IP address.")
    if not 1 <= args.port <= 65535:
        raise SystemExit("--port must be between 1 and 65535.")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    server = ARAServer(args.host, args.port)
    url = f"http://127.0.0.1:{args.port}/"
    logger.info("ARA Research Studio listening at %s", url)
    if not args.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down ARA Research Studio")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
