# ARA Conventions

- Target Python 3.11+, use four-space indentation, type hints, and concise docstrings.
- Keep modules focused; group code by the component layout in `AGENTS.md`.
- Use `logging`, never `print`, in library and application code. The CLI may format output through a configured logger/console adapter.
- Raise domain-specific, actionable errors; do not silently swallow exceptions.
- Put configuration in `config.yaml` and `ARA_*` environment variables. Never hardcode credentials or machine-specific paths.
- Keep model/network initialization lazy so importing modules does not access the network or load weights.
- Use deterministic seeds for training and stable IDs for chunks and traces.
- Name tests `tests/test_<module>.py`; use fixtures and mocks for external services.
- Commit completed tasks as `[<TASK-ID>] <short description>`.

