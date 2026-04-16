# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Django 5.1 event registration system for Dynamobile (annual cycling event). Handles participant signup, billing, financial accounting, newsletter subscriptions, and OVH mailing list integration. Python 3.13, SQLite, Bootstrap 5 frontend. A parallel `reunion/` app manages a 30-year reunion event with a near-identical flow.

## Package Management

Use `uv` (not pip) for all dependency management:

```bash
uv sync                  # install dependencies
uv add <package>         # add a dependency
uv run <command>         # run a command in the project environment
```

## Common Commands

```bash
# Development server
uv run python manage.py runserver

# Database migrations
uv run python manage.py makemigrations
uv run python manage.py migrate

# Compile SCSS (also runs on collectstatic)
uv run python manage.py compilescss

# Translations
uv run python manage.py makemessages -l fr
uv run python manage.py compilemessages

# Tests
uv run pytest                                       # all tests
uv run pytest tests/features/login.feature         # single feature
uv run pytest --cov                                 # with coverage report

# Linting & formatting
uv run ruff check .
uv run ruff format .
pre-commit run --all-files
```

## Architecture

### Apps

- **signup2023/** — Main signup flow (participants, day selection, waiting list, billing)
- **reunion/** — 30-year reunion signup (same structure as signup2023, different URL prefix `/dFUeJlGX/`)
- **accounts/** — Financial accounting: bank operations, bills, expense reports, chart of accounts
- **newsletter/** — Email subscription form backed by OVH mailing lists
- **connectors/** — External API clients (OVH mailing list in `ovh.py`)
- **dynasignup/** — Project settings, root URLs, shared mixins

### Signup Flow (signup2023)

The user flow is strictly linear and enforced by `SignupStartedMixin`:

1. `HomePage` (`/`) — countdown timer, login prompt
2. `CreateGroupView` (`/participants/`) — add participants via inline formset
3. `SelectDayView` (`/select_days/`) — choose event days per participant
4. `GroupExtraEditView` (`/extra_info/`) — mechanic skills, road book preference
5. `GroupReviewView` (`/validate/`) — review, creates `Bill`
6. `CompletedSignupView` (`/review/`) — confirmation, sends email

`SignupStartedMixin` enforces: authenticated user → signup timeline open → creates/retrieves the user's `Signup` → redirects on-hold signups appropriately.

### Key Models

- `Signup` — one per user group; has `on_hold`, `on_hold_vae`, `on_hold_partial` booleans and a `validated` state
- `Participant` — individual attendee linked to a Signup; age is computed at query time against `DYNAMOBILE_LAST_DAY` via a custom manager annotation
- `Bill` (signup2023) — auto-created on validation; tracks payment status
- `accounts.Operation` / `accounts.Bill` / `accounts.ExpenseReport` — financial records with GenericForeignKey (`OperationValidation`) for polymorphic justifications

### Authentication

Magic link (passwordless email login) via `django-magiclink`. Admin uses standard username/password. Users in the `"préinscriptions"` group may sign up before `DYNAMOBILE_START_SIGNUP`.

### Waiting List

Participants placed on hold are ranked using a PostgreSQL-style `Window(RowNumber())` with multiple priority tiers (full vs. partial signup). The `on_hold` / `on_hold_vae` / `on_hold_partial` flags drive this logic in `signup2023/models.py`.

### Static Files & Styling

SCSS source lives in `static_src/scss/`; `custom_bootstrap.scss` imports Bootstrap 5 partials. `django-sass-processor` compiles at runtime in dev. WhiteNoise serves compressed static files in production. The compiled `static/` directory is git-ignored.

### Internationalization

Default locale is `fr-BE`; `nl-BE` is also supported. Use `gettext_lazy` for model/form strings and `{% trans %}` in templates. Locale files are in `locale/`.

## Environment Variables

Configured via `python-decouple`. Key variables:

| Variable | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | insecure default | Django secret key |
| `DEBUG` | `False` | Debug mode |
| `DYNAMOBILE_START_SIGNUP` | `2026-04-22 20:00:00` | When signup opens |
| `DYNAMOBILE_MAX_PARTICIPANTS` | `120` | Participant cap |
| `DYNAMOBILE_MAX_VAE_PARTICIPANTS` | `20` | VAE participant cap |
| `OVH_API_KEY/SECRET/CONSUMER` | — | OVH mailing list API |
| `EMAIL_*` | console backend | Email sending |

## Testing

Tests use `pytest-bdd` with Selenium (Chrome driver). Feature files are in `tests/features/`, step definitions in `tests/step_defs/`. Fixtures (participant, admin, staff) are in `tests/conftest.py` and use `model-bakery`. Coverage minimum is 80% across `accounts`, `dynasignup`, `newsletter`, `reunion`, `signup2023`.

## Commits

Follow Conventional Commits / SemVer: `feat:`, `fix:`, `chore:`, etc.

## Conventions

- Forms use `inlineformset_factory` for multi-record editing (participants, day selections, extra info)
- Crispy Forms with `FloatingField` and Bootstrap 5 grid (`Row`/`Column`) for layout
- QuerySet annotations (not model fields) for computed values like age and financial totals — see `ParticipantManager` and `SignupManager`
- Admin customizations are split across `admin.py`, `admin_custom_views.py`, and `admin_operation.py` in each app
- The `accounts` app uses `ExpenditureChoices` and `IncomeChoices` enums as a chart of accounts
