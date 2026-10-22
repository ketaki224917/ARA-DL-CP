# ARA — Autonomous Research & Report Agent

ARA is a local-first research assistant that builds reports from retrieved evidence and attaches chunk-level citations to factual claims. The implementation is being built in phases; current scope and resume instructions are tracked in [`docs/state/HANDOFF.md`](docs/state/HANDOFF.md).

## Development

Python 3.11+ and `uv` are required. Once dependencies are locked, use `make setup` to create the environment and `make test` to run the test suite.

See [`AGENTS.md`](AGENTS.md) for the project specification and [`docs/state/TODO.md`](docs/state/TODO.md) for implementation status.

