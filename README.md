# Task Manager — Full Stack Application
> Flutter + FastAPI + SQLite/PostgreSQL | Production-Ready

---

## Quick start

```bash
# Backend — SQLite (zero config)
cd backend
make env          # creates .env from .env.example
make install-dev
make dev          # http://127.0.0.1:8000/docs

# Backend — PostgreSQL (Docker)
make docker-up    # http://localhost:8000/docs

# Flutter
cd flutter_app
flutter pub get
flutter run
```

---

## Project layout

```
task_manager/
├── .github/workflows/ci.yml      CI pipeline (test · lint · docker build)
├── CONTRIBUTING.md               Full developer guide
├── backend/
│   ├── main.py                   FastAPI routes + business logic
│   ├── database.py               SQLAlchemy engine (SQLite ↔ PostgreSQL)
│   ├── models.py                 ORM Task model
│   ├── schemas.py                Pydantic schemas
│   ├── alembic/                  Schema migrations
│   │   └── versions/             001_initial · 002_indexes
│   ├── tests/                    pytest suite (75+ test cases)
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── render.yaml               One-click Render.com deploy
│   ├── Makefile                  All developer shortcuts
│   └── .env.example
└── flutter_app/lib/
    ├── models/                   Task data class
    ├── services/                 API client · state · draft persistence
    ├── screens/                  List screen · form screen
    └── widgets/                  TaskCard · Theme · EmptyState · Banner
```

---

## Data model

| Field | Type | Notes |
|-------|------|-------|
| id | int | Auto-generated |
| title | String(255) | Required, trimmed |
| description | String(2000) | Optional |
| due_date | Date | Optional |
| status | Enum | To-Do / In Progress / Done |
| blocked_by | int? | References another task's id |
| recurring | Enum | None / Daily / Weekly |

---

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | /tasks | List + filter (status, search) |
| POST | /tasks | Create (+2 s async delay) |
| PUT | /tasks/{id} | Update (+2 s async delay) |
| DELETE | /tasks/{id} | Delete + clear orphan refs |
| GET | / | Health check |

All error responses: `{ "error": true, "detail": "..." }`

---

## Key features

### Async handling
`asyncio.sleep(2)` on POST/PUT yields the event loop — the API stays responsive
and the Flutter Save button is disabled with a spinner during the wait.

### Recurring task spawn
When status transitions to Done and recurring ≠ None, a new task is created:
- Daily → due_date + 1 day, status = To-Do
- Weekly → due_date + 7 days, status = To-Do
Fires only once per Done-transition (idempotent guard).

### Dependency / blocking
- `blocked_by` references another task's id.
- Flutter greys out and disables cards where the blocker is not Done.
- Self-block rejected (422). Circular deps caught by DFS (422).
- Deleting a blocker clears `blocked_by` on all dependents.

### Draft persistence
Every keystroke on the task form is saved to SharedPreferences.
Re-opening the form offers to restore the draft.

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| DATABASE_URL | sqlite:///./tasks.db | Full SQLAlchemy DB URL |
| ALLOWED_ORIGINS | * | Comma-separated CORS origins |
| LOG_LEVEL | INFO | Python log level |
| PORT | 8000 | Uvicorn bind port |

---

## Deployment

### Docker
```bash
cd backend && make docker-up
```

### Render.com
Push to GitHub → Connect repo → Render detects `render.yaml` automatically.
Provisions managed PostgreSQL + Python web service with one click.

### Manual (any Linux host)
```bash
pip install -r requirements.txt
DATABASE_URL=postgresql://... uvicorn main:app --host 0.0.0.0 --port 10000
```

---

## Testing

```bash
cd backend
make test        # full suite, in-memory SQLite
make test-cov    # with HTML coverage report
```

75+ test cases across four files:
`test_crud` · `test_dependencies` · `test_recurring` · `test_error_handling`
