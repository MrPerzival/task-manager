# Contributing Guide

Thank you for contributing to Task Manager! This document explains the full
development workflow from first clone to submitting a pull request.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Project structure](#project-structure)
3. [Backend setup](#backend-setup)
4. [Flutter setup](#flutter-setup)
5. [Running the full stack](#running-the-full-stack)
6. [Database migrations](#database-migrations)
7. [Testing](#testing)
8. [Code style](#code-style)
9. [Pull request checklist](#pull-request-checklist)

---

## Prerequisites

| Tool | Minimum version | Purpose |
|------|----------------|---------|
| Python | 3.11 | Backend runtime |
| pip | 23+ | Python packages |
| Docker + Compose | 24+ | PostgreSQL + containerised backend |
| Flutter | 3.10 | Mobile frontend |
| Dart | 3.0 | Flutter language |
| make | any | Developer shortcuts |

---

## Project structure

```
task_manager/
├── .github/
│   └── workflows/
│       └── ci.yml              ← GitHub Actions CI
│
├── backend/
│   ├── main.py                 ← FastAPI app, all routes
│   ├── database.py             ← Engine, session, get_db()
│   ├── models.py               ← SQLAlchemy ORM
│   ├── schemas.py              ← Pydantic request/response
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── Makefile                ← Developer shortcuts
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── render.yaml             ← Render.com deployment
│   ├── .env.example
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       ├── 001_initial_create_tasks_table.py
│   │       └── 002_add_indexes.py
│   └── tests/
│       ├── conftest.py
│       ├── test_crud.py
│       ├── test_dependencies.py
│       ├── test_recurring.py
│       └── test_error_handling.py
│
└── flutter_app/
    └── lib/
        ├── main.dart
        ├── models/task.dart
        ├── services/
        │   ├── api_service.dart
        │   ├── draft_service.dart
        │   └── task_provider.dart
        ├── screens/
        │   ├── task_list_screen.dart
        │   └── task_form_screen.dart
        └── widgets/
            ├── app_theme.dart
            ├── task_card.dart
            ├── connection_banner.dart
            └── empty_state.dart
```

---

## Backend setup

```bash
cd backend

# 1. Copy and configure environment
make env          # copies .env.example → .env

# 2. Install dependencies
make install-dev  # production deps + pytest, ruff, black

# 3. Start the dev server (SQLite, hot-reload)
make dev
# API:  http://127.0.0.1:8000
# Docs: http://127.0.0.1:8000/docs
```

---

## Flutter setup

```bash
cd flutter_app

flutter pub get
flutter run          # starts on connected device / emulator
```

> **Physical device**: set `ApiConfig.baseUrl` in `lib/services/api_service.dart`
> to your machine's LAN IP, e.g. `http://192.168.1.10:8000`.

---

## Running the full stack

```bash
cd backend
make docker-up     # starts PostgreSQL + API on http://localhost:8000

# View logs
make docker-logs

# Stop (keep DB volume)
make docker-down

# Stop + wipe DB
make docker-clean
```

---

## Database migrations

We use **Alembic** for schema migrations.

```bash
cd backend

# Apply all pending migrations
make migrate

# Create a new migration (autogenerate from model changes)
make migrate-create MSG="add priority column to tasks"

# Roll back one step
make migrate-rollback

# Show history
make migrate-history

# Check current revision
make migrate-status
```

### Migration rules

1. **Never edit existing migration files** once they have been applied to any
   shared environment (staging, production).  Create a new migration instead.
2. Every migration must have a valid `downgrade()` implementation.
3. Test both `upgrade` and `downgrade` locally before opening a PR.

```bash
alembic upgrade head    # apply
alembic downgrade -1    # verify rollback works
alembic upgrade head    # re-apply to confirm idempotency
```

---

## Testing

```bash
cd backend

# Run the full suite (fast, in-memory SQLite)
make test

# Verbose output
make test-v

# Stop on first failure
make test-fast

# Coverage report (requires pytest-cov)
make test-cov
# open htmlcov/index.html
```

### Writing tests

- All tests live in `tests/`.
- Use the `make_task` fixture for creating tasks — it handles POST and assertion.
- Patch `main.asyncio.sleep` in every test module:
  ```python
  @pytest.fixture(autouse=True)
  def no_sleep(monkeypatch):
      monkeypatch.setattr("main.asyncio.sleep", AsyncMock(return_value=None))
  ```
- Tests must be hermetic: no shared state, no network calls, no file I/O.
- Group related tests in classes (`class TestRecurring:`) for readable output.

### Test categories

| File | What it tests |
|------|--------------|
| `test_crud.py` | GET / POST / PUT / DELETE happy paths + validation |
| `test_dependencies.py` | blocked_by, self-block, DFS circular detection |
| `test_recurring.py` | Daily/Weekly spawn, idempotency, no-due-date case |
| `test_error_handling.py` | Error envelope shape, edge-case inputs, HTTP contract |

---

## Code style

### Python (backend)

```bash
make lint          # ruff check
make lint-fix      # ruff auto-fix
make format        # black formatting
make format-check  # CI dry-run
```

Rules:
- Line length: 100 (ruff E501 is ignored — black handles wrapping).
- Type hints on all public function signatures.
- Docstrings on all route handlers and non-trivial helpers.
- No bare `except:` — always catch a specific exception type.

### Dart (Flutter)

- Follow the official [Dart style guide](https://dart.dev/guides/language/effective-dart/style).
- Run `flutter analyze` before committing.
- Use `const` constructors wherever possible.
- Prefer named parameters for widget constructors with more than two arguments.

---

## Pull request checklist

Before opening a PR, confirm:

- [ ] `make test` passes with zero failures
- [ ] `make lint` and `make format-check` pass
- [ ] New features have corresponding tests
- [ ] Migration added if the ORM model changed
- [ ] Both `upgrade` and `downgrade` tested locally
- [ ] `flutter analyze` passes with zero errors
- [ ] `CONTRIBUTING.md` updated if the workflow changed
- [ ] PR description explains *what* changed and *why*
