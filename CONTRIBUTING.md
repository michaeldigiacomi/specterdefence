# Contributing to SpecterDefence

## Development setup

```bash
git clone https://github.com/michaeldigiacomi/specterdefence.git
cd specterdefence
poetry install          # backend (Python 3.11+)
cd frontend && npm install   # frontend (Node 18+)
```

Install pre-commit hooks (`pre-commit install`) — they run Black, Ruff, MyPy, Bandit, ESLint, and Hadolint.

## Quality checks

Everything is wired through the Makefile:

```bash
make lint           # ruff check .
make format-check   # black --check .
make type-check     # mypy src/
make security-check # bandit
make test           # pytest with coverage (source: src/, 80% floor)
make validate       # all of the above
```

Keep new code typed, formatted, and test-covered. The CI workflows (`.github/workflows/backend.yml`, `frontend.yml`, `agent.yml`, `marketing.yml`) run these tools on push/PR to `main`; currently lint/format/type failures are reported but non-blocking there, so the pre-commit hooks are the enforcement point.

## Conventions

- Python: Black formatting, Ruff linting (default rules), type annotations on public functions, complex functions refactored under complexity limits.
- Frontend: strict TypeScript per `frontend/tsconfig.json` and `frontend/STANDARDS.md`.
- Tests: `tests/unit` and `tests/integration`, pytest-asyncio; fixtures in `tests/conftest.py`/`tests/factories.py`.

## Submitting changes

1. Fork, branch (`feature/...`), keep commits focused.
2. Run `make validate` and `pre-commit run --all-files` locally.
3. Open a PR describing the change and its user-visible impact.
