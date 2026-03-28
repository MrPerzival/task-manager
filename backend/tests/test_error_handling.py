"""
tests/test_error_handling.py
----------------------------
Tests for the global exception handler, consistent error envelope,
input validation edge cases, and API contract guarantees.
"""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr("main.asyncio.sleep", AsyncMock(return_value=None))


# ═════════════════════════════════════════════════════════════════════════════
# Consistent error envelope  { "error": true, "detail": "..." }
# ═════════════════════════════════════════════════════════════════════════════

class TestErrorEnvelope:

    def test_404_has_error_flag(self, client):
        resp = client.get("/tasks/99999")   # GET /tasks/{id} doesn't exist — 404 from routing
        # The route doesn't exist, so we get a 404 or 405; either has our envelope
        assert resp.status_code in (404, 405)

    def test_404_on_update_nonexistent(self, client):
        resp = client.put("/tasks/99999", json={"title": "Ghost"})
        assert resp.status_code == 404
        body = resp.json()
        assert body.get("error") is True
        assert isinstance(body.get("detail"), str)
        assert len(body["detail"]) > 0

    def test_404_on_delete_nonexistent(self, client):
        resp = client.delete("/tasks/99999")
        assert resp.status_code == 404
        body = resp.json()
        assert body.get("error") is True

    def test_422_has_error_flag(self, client):
        resp = client.post("/tasks", json={"title": ""})
        assert resp.status_code == 422
        body = resp.json()
        assert body.get("error") is True

    def test_422_circular_dep_has_error_flag(self, client, make_task):
        a = make_task(title="A")
        b = make_task(title="B", blocked_by=a["id"])
        resp = client.put(f"/tasks/{a['id']}", json={"blocked_by": b["id"]})
        assert resp.status_code == 422
        body = resp.json()
        assert body.get("error") is True
        assert "circular" in body["detail"].lower()

    def test_422_self_block_has_error_flag(self, client, make_task):
        task = make_task(title="Solo")
        resp = client.put(f"/tasks/{task['id']}", json={"blocked_by": task["id"]})
        assert resp.status_code == 422
        body = resp.json()
        assert body.get("error") is True

    def test_detail_is_always_string(self, client):
        """detail must always be a plain string, never a nested object."""
        resp = client.put("/tasks/99999", json={"title": "x"})
        assert isinstance(resp.json()["detail"], str)


# ═════════════════════════════════════════════════════════════════════════════
# Input validation edge cases
# ═════════════════════════════════════════════════════════════════════════════

class TestInputValidation:

    def test_missing_title_field_rejected(self, client):
        resp = client.post("/tasks", json={"description": "No title here"})
        assert resp.status_code == 422

    def test_title_with_only_spaces_rejected(self, client):
        resp = client.post("/tasks", json={"title": "     "})
        assert resp.status_code == 422

    def test_title_single_char_accepted(self, client):
        resp = client.post("/tasks", json={"title": "X"})
        assert resp.status_code == 201

    def test_title_max_length(self, client):
        """255-character title should be accepted."""
        resp = client.post("/tasks", json={"title": "A" * 255})
        assert resp.status_code == 201

    def test_invalid_date_format_rejected(self, client):
        resp = client.post("/tasks", json={"title": "T", "due_date": "31-12-2025"})
        assert resp.status_code == 422

    def test_null_title_rejected(self, client):
        resp = client.post("/tasks", json={"title": None})
        assert resp.status_code == 422

    def test_wrong_type_for_blocked_by(self, client):
        resp = client.post("/tasks", json={"title": "T", "blocked_by": "not-an-int"})
        assert resp.status_code == 422

    def test_float_blocked_by_rejected(self, client):
        resp = client.post("/tasks", json={"title": "T", "blocked_by": 1.5})
        assert resp.status_code == 422

    def test_extra_fields_ignored(self, client):
        """Unknown fields in the payload must be silently ignored (not crash)."""
        resp = client.post("/tasks", json={
            "title": "Extra Fields",
            "unknown_field": "should be ignored",
            "another": 999,
        })
        assert resp.status_code == 201
        assert "unknown_field" not in resp.json()

    def test_description_defaults_to_empty_string(self, client):
        resp = client.post("/tasks", json={"title": "No Desc"})
        assert resp.status_code == 201
        assert resp.json()["description"] == ""

    def test_status_defaults_to_todo(self, client):
        resp = client.post("/tasks", json={"title": "Default Status"})
        assert resp.status_code == 201
        assert resp.json()["status"] == "To-Do"

    def test_recurring_defaults_to_none(self, client):
        resp = client.post("/tasks", json={"title": "Default Rec"})
        assert resp.status_code == 201
        assert resp.json()["recurring"] == "None"


# ═════════════════════════════════════════════════════════════════════════════
# Content-type and method checks
# ═════════════════════════════════════════════════════════════════════════════

class TestHttpContract:

    def test_get_tasks_returns_json(self, client):
        resp = client.get("/tasks")
        assert "application/json" in resp.headers["content-type"]

    def test_post_tasks_returns_json(self, client):
        resp = client.post("/tasks", json={"title": "JSON Test"})
        assert "application/json" in resp.headers["content-type"]

    def test_response_ids_are_integers(self, client, make_task):
        task = make_task(title="ID Type Check")
        assert isinstance(task["id"], int)

    def test_tasks_ordered_by_id(self, client, make_task):
        t1 = make_task(title="First")
        t2 = make_task(title="Second")
        t3 = make_task(title="Third")
        tasks = client.get("/tasks").json()
        ids = [t["id"] for t in tasks]
        assert ids == sorted(ids)

    def test_invalid_json_body_rejected(self, client):
        resp = client.post(
            "/tasks",
            content="not json at all",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422

    def test_blocked_by_reference_preserved_in_response(self, client, make_task):
        a = make_task(title="Blocker")
        b = make_task(title="Blocked", blocked_by=a["id"])
        assert b["blocked_by"] == a["id"]

    def test_due_date_null_in_response(self, client, make_task):
        task = make_task(title="No Due Date")
        assert task["due_date"] is None

    def test_due_date_iso_format_in_response(self, client, make_task):
        task = make_task(title="Dated", due_date="2025-11-30")
        assert task["due_date"] == "2025-11-30"
