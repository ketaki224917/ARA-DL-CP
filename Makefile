.PHONY: prepare-runtime setup ingest serve serve-rag serve-web-search serve-dl-model web run eval eval-rag train test lint tts-model tts-smoke

UV ?= uv

# Keep tool caches and temporary files beside the checkout on the same drive.
ARA_LOCAL_TOOLS := $(CURDIR)/.tools
override UV_CACHE_DIR := $(ARA_LOCAL_TOOLS)/uv-cache
override UV_PYTHON_INSTALL_DIR := $(ARA_LOCAL_TOOLS)/uv-python
override TEMP := $(ARA_LOCAL_TOOLS)/tmp
override TMP := $(TEMP)
export UV_CACHE_DIR UV_PYTHON_INSTALL_DIR TEMP TMP

prepare-runtime:
	mkdir -p "$(TEMP)"

setup: prepare-runtime
	$(UV) sync --locked --extra dev --extra dl --extra tts

ingest: prepare-runtime
	$(UV) run --locked ara ingest

serve: prepare-runtime
	$(UV) run --locked ara serve-mcp --server rag

serve-rag: prepare-runtime
	$(UV) run --locked ara serve-mcp --server rag

serve-web-search: prepare-runtime
	$(UV) run --locked ara serve-mcp --server web-search

serve-dl-model: prepare-runtime
	$(UV) run --locked ara serve-mcp --server dl-model

web: prepare-runtime
	$(UV) run --locked python -m ara.web_app

run: prepare-runtime
	$(UV) run --locked ara run --topic "$(TOPIC)" $(ARGS)

eval: prepare-runtime
	$(UV) run --locked ara eval $(ARGS)

eval-rag: prepare-runtime
	$(UV) run --locked ara rag-eval $(ARGS)

train: prepare-runtime
	$(UV) run --locked ara train $(ARGS)

test: prepare-runtime
	$(UV) run --locked pytest

lint: prepare-runtime
	$(UV) run --locked ruff check .

tts-model: prepare-runtime
	$(UV) run --locked --extra tts python -m ara.generative.tts --download-voice

tts-smoke: prepare-runtime
	$(UV) run --locked --extra tts python scripts/tts_synthesis_smoke.py

