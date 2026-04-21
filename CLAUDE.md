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
- Test both positive and negative scenarios
- Always write unit tests and check that they pass for new features

- Use `pytest-django` for database access and fixtures
- Use `pytest-cov` for coverage reporting
- Use `pytest-xdist` for parallel test execution
- Use `pytest-randomly` for randomized test order
- Use `pytest-sugar` for nicer test output
- Use `pytest-rerunfailures` for rerunning failed tests
- Use `pytest-timeout` for test timeouts
- Use `pytest-django-queries` for query count assertions

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

Coverage is reported automatically during test runs (configured via `pytest-cov`).

## Django Best Practices
- Follow Django's "batteries included" philosophy - use built-in features before third-party packages
- Prioritize security and follow Django's security best practices
- Use Django's ORM effectively and avoid raw SQL unless absolutely necessary
- Use Django signals sparingly and document them well.

## Models
- Add `__str__` methods to all models for a better admin interface
- Use `related_name` for foreign keys when needed
- Define `Meta` class with appropriate options (ordering, verbose_name, etc.)
- Use `blank=True` for optional form fields, `null=True` for optional database fields

## Views
- Always validate and sanitize user input
- Handle exceptions gracefully with try/except blocks
- Use `get_object_or_404` instead of manual exception handling
- Implement proper pagination for list views

## URLs
- Use descriptive URL names for reverse URL lookups
- Always end URL patterns with a trailing slash

## Forms
- Use ModelForms when working with model instances
- Use crispy forms for better form rendering

## Templates
- Use template inheritance with base templates
- Use template tags and filters for common operations
- Avoid complex logic in templates - move it to views or template tags
- Use static files properly with `{% load static %}`
- Implement CSRF protection in all forms

## Settings
- Use environment variables in a single `settings.py` file
- Never commit secrets to version control

## Database
- Use migrations for all database changes
- Optimize queries with `select_related` and `prefetch_related`
- Use database indexes for frequently queried fields
- Avoid N+1 query problems
