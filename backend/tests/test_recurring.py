"""
tests/test_recurring.py
-----------------------
Tests for the recurring task auto-spawn system.

Rules under test
----------------
• Marking a Daily task Done → new task with due_date + 1 day, status To-Do.
• Marking a Weekly task Done → new task with due_date + 7 days, status To-Do.
• Non-recurring task Done → no new task spawned.
• Spawn only fires on the Done *transition* (not if already Done).
• Spawned task copies all fields (title, description, blocked_by, recurring).
• Spawned task gets a new unique ID.
• Tasks with no due_date still spawn (next due_date stays None).
"""

import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr("main.asyncio.sleep", AsyncMock(return_value=None))


# ── Helpers ───────────────────────────────────────────────────────────────────

def all_tasks(client) -> list[dict]:
    return client.get("/tasks").json()


def tasks_by_title(client, title: str) -> list[dict]:
    return [t for t in all_tasks(client) if t["title"] == title]


# ═════════════════════════════════════════════════════════════════════════════
# Daily recurring
# ═════════════════════════════════════════════════════════════════════════════

class TestDailyRecurring:

    def test_daily_spawns_new_task_on_done(self, client, make_task):
        task = make_task(title="Daily Chore", due_date="2025-06-01", recurring="Daily")

        resp = client.put(f"/tasks/{task['id']}", json={"status": "Done"})
        assert resp.status_code == 200

        # Expect 2 tasks with this title (original + new occurrence)
        matches = tasks_by_title(client, "Daily Chore")
        assert len(matches) == 2

    def test_daily_new_task_due_date_plus_one(self, client, make_task):
        task = make_task(title="Daily Task", due_date="2025-06-10", recurring="Daily")
        client.put(f"/tasks/{task['id']}", json={"status": "Done"})

        matches = tasks_by_title(client, "Daily Task")
        next_task = next(t for t in matches if t["id"] != task["id"])
        assert next_task["due_date"] == "2025-06-11"

    def test_daily_new_task_status_is_todo(self, client, make_task):
        task = make_task(title="Daily Reset", due_date="2025-01-01", recurring="Daily")
        client.put(f"/tasks/{task['id']}", json={"status": "Done"})

        matches = tasks_by_title(client, "Daily Reset")
        next_task = next(t for t in matches if t["id"] != task["id"])
        assert next_task["status"] == "To-Do"

    def test_daily_original_task_preserved(self, client, make_task):
        task = make_task(title="Daily Preserve", due_date="2025-03-01", recurring="Daily")
        client.put(f"/tasks/{task['id']}", json={"status": "Done"})

        matches = tasks_by_title(client, "Daily Preserve")
        original = next(t for t in matches if t["id"] == task["id"])
        assert original["status"] == "Done"
        assert original["due_date"] == "2025-03-01"

    def test_daily_new_task_has_new_id(self, client, make_task):
        task = make_task(title="Daily ID Test", due_date="2025-05-05", recurring="Daily")
        client.put(f"/tasks/{task['id']}", json={"status": "Done"})

        matches = tasks_by_title(client, "Daily ID Test")
        ids = [t["id"] for t in matches]
        assert len(set(ids)) == 2  # two distinct IDs

    def test_daily_copies_description(self, client, make_task):
        task = make_task(
            title="Daily Copy",
            description="Important notes",
            due_date="2025-07-01",
            recurring="Daily",
        )
        client.put(f"/tasks/{task['id']}", json={"status": "Done"})

        matches = tasks_by_title(client, "Daily Copy")
        next_task = next(t for t in matches if t["id"] != task["id"])
        assert next_task["description"] == "Important notes"

    def test_daily_copies_recurring_field(self, client, make_task):
        task = make_task(title="Daily Self-Rep", due_date="2025-08-01", recurring="Daily")
        client.put(f"/tasks/{task['id']}", json={"status": "Done"})

        matches = tasks_by_title(client, "Daily Self-Rep")
        next_task = next(t for t in matches if t["id"] != task["id"])
        assert next_task["recurring"] == "Daily"


# ═════════════════════════════════════════════════════════════════════════════
# Weekly recurring
# ═════════════════════════════════════════════════════════════════════════════

class TestWeeklyRecurring:

    def test_weekly_spawns_new_task_on_done(self, client, make_task):
        task = make_task(title="Weekly Review", due_date="2025-06-01", recurring="Weekly")
        client.put(f"/tasks/{task['id']}", json={"status": "Done"})

        matches = tasks_by_title(client, "Weekly Review")
        assert len(matches) == 2

    def test_weekly_new_task_due_date_plus_seven(self, client, make_task):
        task = make_task(title="Weekly +7", due_date="2025-06-01", recurring="Weekly")
        client.put(f"/tasks/{task['id']}", json={"status": "Done"})

        matches = tasks_by_title(client, "Weekly +7")
        next_task = next(t for t in matches if t["id"] != task["id"])
        assert next_task["due_date"] == "2025-06-08"   # +7 days

    def test_weekly_new_task_status_is_todo(self, client, make_task):
        task = make_task(title="Weekly Status", due_date="2025-06-15", recurring="Weekly")
        client.put(f"/tasks/{task['id']}", json={"status": "Done"})

        matches = tasks_by_title(client, "Weekly Status")
        next_task = next(t for t in matches if t["id"] != task["id"])
        assert next_task["status"] == "To-Do"

    def test_weekly_month_boundary(self, client, make_task):
        """Week crossing a month boundary: June 28 + 7 = July 5."""
        task = make_task(title="Month Boundary", due_date="2025-06-28", recurring="Weekly")
        client.put(f"/tasks/{task['id']}", json={"status": "Done"})

        matches = tasks_by_title(client, "Month Boundary")
        next_task = next(t for t in matches if t["id"] != task["id"])
        assert next_task["due_date"] == "2025-07-05"

    def test_weekly_year_boundary(self, client, make_task):
        """Week crossing a year boundary: Dec 29 + 7 = Jan 5."""
        task = make_task(title="Year Boundary", due_date="2025-12-29", recurring="Weekly")
        client.put(f"/tasks/{task['id']}", json={"status": "Done"})

        matches = tasks_by_title(client, "Year Boundary")
        next_task = next(t for t in matches if t["id"] != task["id"])
        assert next_task["due_date"] == "2026-01-05"


# ═════════════════════════════════════════════════════════════════════════════
# No-recurring tasks — must NOT spawn
# ═════════════════════════════════════════════════════════════════════════════

class TestNoRecurring:

    def test_non_recurring_done_no_spawn(self, client, make_task):
        task = make_task(title="One-off Task", recurring="None")
        client.put(f"/tasks/{task['id']}", json={"status": "Done"})

        matches = tasks_by_title(client, "One-off Task")
        assert len(matches) == 1

    def test_non_recurring_count_stays_same(self, client, make_task):
        make_task(title="T1", recurring="None")
        make_task(title="T2", recurring="None")
        t3 = make_task(title="T3", recurring="None")

        before_count = len(all_tasks(client))
        client.put(f"/tasks/{t3['id']}", json={"status": "Done"})
        after_count = len(all_tasks(client))

        assert before_count == after_count


# ═════════════════════════════════════════════════════════════════════════════
# Idempotency — already-Done tasks must NOT spawn again
# ═════════════════════════════════════════════════════════════════════════════

class TestRecurringIdempotency:

    def test_done_to_done_no_extra_spawn(self, client, make_task):
        """
        Updating a task that is already 'Done' to 'Done' again
        must not create a second recurring occurrence.
        """
        task = make_task(title="Idempotent", due_date="2025-09-01", recurring="Daily")

        # First transition → spawn 1 new task
        client.put(f"/tasks/{task['id']}", json={"status": "Done"})
        after_first = len(tasks_by_title(client, "Idempotent"))
        assert after_first == 2

        # Second PUT with status=Done (already Done) → no new spawn
        client.put(f"/tasks/{task['id']}", json={"status": "Done"})
        after_second = len(tasks_by_title(client, "Idempotent"))
        assert after_second == 2  # still 2, not 3


# ═════════════════════════════════════════════════════════════════════════════
# No due_date — recurring spawn still works, next due_date stays None
# ═════════════════════════════════════════════════════════════════════════════

class TestRecurringNoDueDate:

    def test_daily_no_due_date_spawns(self, client, make_task):
        task = make_task(title="Dateless Daily", recurring="Daily")
        # No due_date supplied
        client.put(f"/tasks/{task['id']}", json={"status": "Done"})

        matches = tasks_by_title(client, "Dateless Daily")
        assert len(matches) == 2

    def test_daily_no_due_date_next_has_no_due_date(self, client, make_task):
        task = make_task(title="Dateless Next", recurring="Daily")
        client.put(f"/tasks/{task['id']}", json={"status": "Done"})

        matches = tasks_by_title(client, "Dateless Next")
        next_task = next(t for t in matches if t["id"] != task["id"])
        assert next_task["due_date"] is None
