# dyn-signup

Django app for managing Dynamobile event registrations.

## Package management

Use `uv` for all package operations:
- Install deps: `uv sync`
- Add a package: `uv add <package>`
- Add a dev package: `uv add --dev <package>`
- Run commands: `uv run <command>`

## Testing

Uses **pytest-bdd** (v8.1.0) with pytest-django.

- Feature files live in `tests/features/`
- Step definitions live in `tests/step_defs/`
- Shared fixtures in `tests/conftest.py`
- BDD base dir is configured in `pyproject.toml` as `tests/features/`

Run full suite:
```
uv run pytest tests/
```

Watch a specific feature during development:
```
uv run ptw tests/step_defs/test_signup2026.py
```

A full test run is automatically triggered before every commit via the pre-commit hook.

## Linting

Uses **ruff** for linting and formatting (auto-fix enabled):
```
uv run ruff check .
uv run ruff format .
```

Rules: isort (`I`), flake8-bugbear (`B`), flake8-quotes (`Q`).

## Coverage

Coverage is reported automatically during test runs (configured via `pytest-cov`). Tracked apps: `accounts`, `dynasignup`, `newsletter`, `reunion`, `signup2023`.
