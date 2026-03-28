"""
tests/test_crud.py
------------------
Full CRUD test coverage for GET / POST / PUT / DELETE /tasks.

Every test function is independent — the `reset_db` autouse fixture
wipes the DB between tests.  The 2-second asyncio.sleep in create/update
routes is patched out so the suite runs in under 5 seconds.
"""

import pytest
from unittest.mock import patch, AsyncMock

# Patch asyncio.sleep globally for all tests in this module so we don't
# wait 2 seconds per create/update call.
pytestmark = pytest.mark.usefixtures("client")


# ── Helper ────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    """Replace asyncio.sleep with a no-op coroutine for all tests here."""
    monkeypatch.setattr("main.asyncio.sleep", AsyncMock(return_value=None))


# ═════════════════════════════════════════════════════════════════════════════
# GET /tasks
# ═════════════════════════════════════════════════════════════════════════════

class TestGetTasks:

    def test_empty_list(self, client):
        """Fresh DB returns an empty array."""
        resp = client.get("/tasks")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_created_tasks(self, client, make_task):
        make_task(title="Alpha")
        make_task(title="Beta")
        resp = client.get("/tasks")
        assert resp.status_code == 200
        titles = [t["title"] for t in resp.json()]
        assert "Alpha" in titles
        assert "Beta" in titles

    def test_filter_by_status(self, client, make_task):
        make_task(title="Todo Task",    status="To-Do")
        make_task(title="Done Task",    status="Done")
        resp = client.get("/tasks?status=Done")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["title"] == "Done Task"

    def test_filter_by_search(self, client, make_task):
        make_task(title="Buy groceries")
        make_task(title="Write tests")
        resp = client.get("/tasks?search=grocer")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["title"] == "Buy groceries"

    def test_search_is_case_insensitive(self, client, make_task):
        make_task(title="Deploy to Production")
        resp = client.get("/tasks?search=DEPLOY")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_combined_status_and_search(self, client, make_task):
        make_task(title="Fix bug",        status="In Progress")
        make_task(title="Fix deployment", status="Done")
        resp = client.get("/tasks?status=In Progress&search=fix")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["title"] == "Fix bug"

    def test_response_shape(self, client, make_task):
        """Every task response must contain exactly the required fields."""
        task = make_task(title="Shape test")
        required_keys = {"id", "title", "description", "due_date",
                         "status", "blocked_by", "recurring"}
        assert required_keys.issubset(task.keys())


# ═════════════════════════════════════════════════════════════════════════════
# POST /tasks
# ═════════════════════════════════════════════════════════════════════════════

class TestCreateTask:

    def test_create_minimal(self, client):
        resp = client.post("/tasks", json={"title": "Minimal Task"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Minimal Task"
        assert data["status"] == "To-Do"
        assert data["recurring"] == "None"
        assert data["blocked_by"] is None
        assert data["id"] > 0

    def test_create_full(self, client):
        payload = {
            "title": "Full Task",
            "description": "All fields set",
            "due_date": "2025-12-31",
            "status": "In Progress",
            "recurring": "Weekly",
        }
        resp = client.post("/tasks", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Full Task"
        assert data["description"] == "All fields set"
        assert data["due_date"] == "2025-12-31"
        assert data["status"] == "In Progress"
        assert data["recurring"] == "Weekly"

    def test_title_is_trimmed(self, client):
        resp = client.post("/tasks", json={"title": "  Padded Title  "})
        assert resp.status_code == 201
        assert resp.json()["title"] == "Padded Title"

    def test_empty_title_rejected(self, client):
        resp = client.post("/tasks", json={"title": ""})
        assert resp.status_code == 422

    def test_whitespace_only_title_rejected(self, client):
        resp = client.post("/tasks", json={"title": "   "})
        assert resp.status_code == 422

    def test_invalid_status_rejected(self, client):
        resp = client.post("/tasks", json={"title": "T", "status": "INVALID"})
        assert resp.status_code == 422

    def test_invalid_recurring_rejected(self, client):
        resp = client.post("/tasks", json={"title": "T", "recurring": "Hourly"})
        assert resp.status_code == 422

    def test_blocked_by_nonexistent_rejected(self, client):
        resp = client.post("/tasks", json={"title": "T", "blocked_by": 9999})
        assert resp.status_code == 404

    def test_blocked_by_valid_task(self, client, make_task):
        blocker = make_task(title="Blocker")
        resp = client.post("/tasks", json={
            "title": "Blocked", "blocked_by": blocker["id"]
        })
        assert resp.status_code == 201
        assert resp.json()["blocked_by"] == blocker["id"]

    def test_ids_are_unique(self, client, make_task):
        t1 = make_task(title="T1")
        t2 = make_task(title="T2")
        assert t1["id"] != t2["id"]


# ═════════════════════════════════════════════════════════════════════════════
# PUT /tasks/{id}
# ═════════════════════════════════════════════════════════════════════════════

class TestUpdateTask:

    def test_update_title(self, client, make_task):
        task = make_task(title="Old Title")
        resp = client.put(f"/tasks/{task['id']}", json={"title": "New Title"})
        assert resp.status_code == 200
        assert resp.json()["title"] == "New Title"

    def test_update_status(self, client, make_task):
        task = make_task(title="Status Test")
        resp = client.put(f"/tasks/{task['id']}", json={"status": "In Progress"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "In Progress"

    def test_update_nonexistent_returns_404(self, client):
        resp = client.put("/tasks/99999", json={"title": "Ghost"})
        assert resp.status_code == 404

    def test_update_empty_title_rejected(self, client, make_task):
        task = make_task(title="Existing")
        resp = client.put(f"/tasks/{task['id']}", json={"title": "  "})
        assert resp.status_code == 422

    def test_title_trimmed_on_update(self, client, make_task):
        task = make_task(title="Original")
        resp = client.put(f"/tasks/{task['id']}", json={"title": "  Trimmed  "})
        assert resp.status_code == 200
        assert resp.json()["title"] == "Trimmed"

    def test_update_due_date(self, client, make_task):
        task = make_task(title="Date Task")
        resp = client.put(f"/tasks/{task['id']}", json={"due_date": "2026-06-15"})
        assert resp.status_code == 200
        assert resp.json()["due_date"] == "2026-06-15"

    def test_partial_update_preserves_other_fields(self, client, make_task):
        task = make_task(title="Full", description="Keep me", status="In Progress")
        resp = client.put(f"/tasks/{task['id']}", json={"title": "Updated Title"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["description"] == "Keep me"
        assert data["status"] == "In Progress"

    def test_update_recurring(self, client, make_task):
        task = make_task(title="Chore")
        resp = client.put(f"/tasks/{task['id']}", json={"recurring": "Daily"})
        assert resp.status_code == 200
        assert resp.json()["recurring"] == "Daily"


# ═════════════════════════════════════════════════════════════════════════════
# DELETE /tasks/{id}
# ═════════════════════════════════════════════════════════════════════════════

class TestDeleteTask:

    def test_delete_existing(self, client, make_task):
        task = make_task(title="To Delete")
        resp = client.delete(f"/tasks/{task['id']}")
        assert resp.status_code == 204

    def test_deleted_task_not_found(self, client, make_task):
        task = make_task(title="Ephemeral")
        client.delete(f"/tasks/{task['id']}")
        resp = client.get("/tasks")
        ids = [t["id"] for t in resp.json()]
        assert task["id"] not in ids

    def test_delete_nonexistent_returns_404(self, client):
        resp = client.delete("/tasks/99999")
        assert resp.status_code == 404

    def test_delete_clears_blocked_by_on_dependents(self, client, make_task):
        """
        When task A (a blocker) is deleted, any tasks that listed A in their
        blocked_by field must have that reference cleared automatically.
        """
        blocker = make_task(title="Blocker A")
        dependent = make_task(title="Blocked B", blocked_by=blocker["id"])

        assert dependent["blocked_by"] == blocker["id"]

        client.delete(f"/tasks/{blocker['id']}")

        resp = client.get("/tasks")
        remaining = {t["id"]: t for t in resp.json()}
        assert dependent["id"] in remaining
        assert remaining[dependent["id"]]["blocked_by"] is None

    def test_delete_response_has_no_body(self, client, make_task):
        task = make_task(title="Silent Delete")
        resp = client.delete(f"/tasks/{task['id']}")
        assert resp.status_code == 204
        assert resp.content == b""


# ═════════════════════════════════════════════════════════════════════════════
# Health check
# ═════════════════════════════════════════════════════════════════════════════

class TestHealthCheck:

    def test_root_returns_ok(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data
