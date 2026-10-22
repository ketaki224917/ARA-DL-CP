.PHONY: setup ingest serve run eval train test lint

setup:
	uv sync --extra dev

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

