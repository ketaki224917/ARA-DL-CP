# Blockers

- [RESOLVED 2026-10-22] ENV-001 Python/uv were absent at session start; installed uv 0.13.4 and managed Python 3.12.15 under ignored `.tools/` without PATH or registry changes.
- [OPEN 2026-10-22] ENV-002 `make` and Ollama are unavailable; WMI denies CPU/RAM/GPU inventory. Needed for the prescribed Makefile workflow, local model smoke test, and full hardware/model selection. Workaround meanwhile: use the Python CLI once installed and keep the model configurable.
- [OPEN 2026-10-22] ENV-003 Sandbox grants read-only access to `.git`; needed to create the required task commits. Workaround meanwhile: finish task files and request approved Git write access for staging/commit.
- [OPEN 2026-10-22] ENV-004 `https://pypi.org/simple/` timed out, so `uv lock` cannot resolve declared packages and pytest/ruff/mypy cannot yet run. Needed for dependency locking and acceptance checks. Workaround meanwhile: keep implementation/test files ready and run Python `compileall`; retry when package-index access is available.

