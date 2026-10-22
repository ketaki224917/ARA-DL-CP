# Blockers

- [RESOLVED 2026-10-22] ENV-001 Python/uv were absent at session start; installed uv 0.13.4 and managed Python 3.12.15 under ignored `.tools/` without PATH or registry changes.
- [OPEN 2026-10-22] ENV-002 `make` and Ollama are unavailable; WMI denies CPU/RAM/GPU inventory. Needed for the prescribed Makefile workflow, local model smoke test, and full hardware/model selection. Workaround meanwhile: use the Python CLI once installed and keep the model configurable.
- [RESOLVED 2026-10-22] ENV-003 Sandbox initially granted read-only access to `.git`; approved escalation was used to create the required P0.2 and P0.3 commits without changing global Git configuration.
- [OPEN 2026-10-22] `https://pypi.org/simple/` timed out, so `uv lock` cannot resolve declared packages and pytest/ruff/mypy cannot yet run. An escalated `uv lock --verbose` first hit an unknown certificate issuer; retrying with `UV_SYSTEM_CERTS=true` downloaded the managed interpreter but made no further progress for over 70 seconds and was interrupted. The user confirmed no trusted internal mirror is available. Needed for dependency locking and acceptance checks. Workaround meanwhile: keep implementation/test files ready and run Python `compileall` plus dependency-free smoke checks; retry when package-index access is available.

