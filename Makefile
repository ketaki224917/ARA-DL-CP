.PHONY: setup ingest serve run eval train test lint tts-model tts-smoke

setup:
	uv sync --extra dev --extra dl --extra tts

ingest:
	uv run ara ingest

serve:
	uv run ara serve-mcp

run:
	uv run ara run --topic "$(TOPIC)"

eval:
	uv run ara eval

train:
	uv run ara train

test:
	uv run pytest

lint:
	uv run ruff check .

tts-model:
	uv run --extra tts python -m ara.generative.tts --download-voice

tts-smoke:
	uv run --extra tts python scripts/tts_synthesis_smoke.py

