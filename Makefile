.PHONY: setup ingest serve serve-rag serve-web-search serve-dl-model run eval eval-rag train test lint tts-model tts-smoke

UV ?= uv

setup:
	$(UV) sync --locked --extra dev --extra dl --extra tts

ingest:
	$(UV) run --locked ara ingest

serve:
	$(UV) run --locked ara serve-mcp --server rag

serve-rag:
	$(UV) run --locked ara serve-mcp --server rag

serve-web-search:
	$(UV) run --locked ara serve-mcp --server web-search

serve-dl-model:
	$(UV) run --locked ara serve-mcp --server dl-model

run:
	$(UV) run --locked ara run --topic "$(TOPIC)" $(ARGS)

eval:
	$(UV) run --locked ara eval $(ARGS)

eval-rag:
	$(UV) run --locked ara rag-eval $(ARGS)

train:
	$(UV) run --locked ara train $(ARGS)

test:
	$(UV) run --locked pytest

lint:
	$(UV) run --locked ruff check .

tts-model:
	$(UV) run --locked --extra tts python -m ara.generative.tts --download-voice

tts-smoke:
	$(UV) run --locked --extra tts python scripts/tts_synthesis_smoke.py

