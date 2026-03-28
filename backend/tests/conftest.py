"""
tests/conftest.py
-----------------
Shared pytest fixtures for the Task Manager test suite.

Strategy
--------
• Uses a fresh in-memory SQLite database for every test session —
  no real PostgreSQL required, tests run offline and in CI.
• Overrides the FastAPI `get_db` dependency so every route automatically
  uses the test session instead of the production one.
• Provides a `client` fixture (httpx TestClient) and higher-level helpers
  such as `make_task` for DRY test bodies.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# We import the app objects from the backend package.
# Adjust sys.path if you run pytest from the repo root rather than backend/.
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import Base, get_db
from main import app

# ── In-memory SQLite engine for tests ────────────────────────────────────────
TEST_DATABASE_URL = "sqlite:///:memory:"

_test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=_test_engine,
)


# ── Session-scoped DB setup / teardown ───────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def create_tables():
    """Create all ORM tables once at the start of the test session."""
    Base.metadata.create_all(bind=_test_engine)
    yield
    Base.metadata.drop_all(bind=_test_engine)


# ── Function-scoped: fresh DB state per test ─────────────────────────────────

@pytest.fixture(autouse=True)
def reset_db():
    """
    Truncate all tables before each test so tests are fully isolated.
    Much faster than recreating the schema from scratch.
    """
    from models import Task  # noqa: F401 — ensure mapper is loaded
    with _test_engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()
    yield


@pytest.fixture
def db_session():
    """Yield a raw SQLAlchemy session for direct DB assertions in tests."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


# ── Override FastAPI dependency ───────────────────────────────────────────────

def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


# ── HTTP client ───────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    """Synchronous TestClient wrapping the FastAPI app."""
    with TestClient(app) as c:
        yield c


# ── Convenience helpers ───────────────────────────────────────────────────────

def make_task_payload(
    title: str = "Test Task",
    description: str = "",
    due_date: str | None = None,
    status: str = "To-Do",
    blocked_by: int | None = None,
    recurring: str = "None",
) -> dict:
    """Return a minimal valid task creation payload."""
    payload = {
        "title": title,
        "description": description,
        "status": status,
        "recurring": recurring,
    }
    if due_date:
        payload["due_date"] = due_date
    if blocked_by is not None:
        payload["blocked_by"] = blocked_by
    return payload


@pytest.fixture
def make_task(client):
    """
    Factory fixture: creates a task via POST /tasks and returns the
    response JSON dict.  The 2-second asyncio.sleep in the real handler
    is bypassed because we monkeypatch it in the test module, or tests
    simply accept the slight delay.

    Usage::
        def test_something(make_task):
            task = make_task(title="Buy milk")
            assert task["status"] == "To-Do"
    """
    def _factory(**kwargs) -> dict:
        resp = client.post("/tasks", json=make_task_payload(**kwargs))
        assert resp.status_code == 201, f"make_task failed: {resp.json()}"
        return resp.json()

    return _factory
