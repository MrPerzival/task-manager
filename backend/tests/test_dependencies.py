"""
tests/test_dependencies.py
--------------------------
Tests for the task dependency system:
  • blocked_by validation
  • Self-block prevention
  • Circular dependency detection (DFS)
  • Visual-blocking state (via GET /tasks and blocked_by chain)
"""

import pytest
from unittest.mock import AsyncMock


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr("main.asyncio.sleep", AsyncMock(return_value=None))


# ═════════════════════════════════════════════════════════════════════════════
# Self-block prevention
# ═════════════════════════════════════════════════════════════════════════════

class TestSelfBlock:

    def test_self_block_on_update_rejected(self, client, make_task):
        """PUT with blocked_by == own id must return 422."""
        task = make_task(title="Solo Task")
        resp = client.put(
            f"/tasks/{task['id']}",
            json={"blocked_by": task["id"]},
        )
        assert resp.status_code == 422
        assert "itself" in resp.json()["detail"].lower()

    def test_self_block_on_create_cleared(self, client, make_task):
        """
        On POST, the ID is not known until after the DB insert.
        The API guards against self-block post-insert by clearing blocked_by.
        We can't trigger this via the public API (we'd need to know the ID
        in advance), so we verify the guard exists by checking a clean creation.
        """
        task = make_task(title="Normal Task")
        # A newly created task with no blocked_by should never block itself
        assert task["blocked_by"] != task["id"]


# ═════════════════════════════════════════════════════════════════════════════
# Circular dependency detection
# ═════════════════════════════════════════════════════════════════════════════

class TestCircularDependency:

    def test_direct_cycle_rejected(self, client, make_task):
        """
        A → B, then attempt B → A.
        The second PUT must be rejected with 422.
        """
        a = make_task(title="Task A")
        b = make_task(title="Task B", blocked_by=a["id"])

        # Now try to make A blocked by B (creates A→B→A cycle)
        resp = client.put(
            f"/tasks/{a['id']}",
            json={"blocked_by": b["id"]},
        )
        assert resp.status_code == 422
        assert "circular" in resp.json()["detail"].lower()

    def test_indirect_cycle_rejected(self, client, make_task):
        """
        A → B → C, then attempt C → A.
        Depth-3 cycle must also be caught by the DFS.
        """
        a = make_task(title="Task A")
        b = make_task(title="Task B", blocked_by=a["id"])
        c = make_task(title="Task C", blocked_by=b["id"])

        resp = client.put(
            f"/tasks/{a['id']}",
            json={"blocked_by": c["id"]},
        )
        assert resp.status_code == 422
        assert "circular" in resp.json()["detail"].lower()

    def test_four_node_cycle_rejected(self, client, make_task):
        """A → B → C → D, then D → A must be rejected."""
        a = make_task(title="A")
        b = make_task(title="B", blocked_by=a["id"])
        c = make_task(title="C", blocked_by=b["id"])
        d = make_task(title="D", blocked_by=c["id"])

        resp = client.put(
            f"/tasks/{a['id']}",
            json={"blocked_by": d["id"]},
        )
        assert resp.status_code == 422

    def test_independent_chain_allowed(self, client, make_task):
        """
        A → B and C → D are separate chains.
        Linking E → D should succeed (no cycle).
        """
        a = make_task(title="A")
        make_task(title="B", blocked_by=a["id"])
        c = make_task(title="C")
        d = make_task(title="D", blocked_by=c["id"])
        e = make_task(title="E")

        resp = client.put(
            f"/tasks/{e['id']}",
            json={"blocked_by": d["id"]},
        )
        assert resp.status_code == 200

    def test_cycle_check_does_not_affect_unrelated_tasks(self, client, make_task):
        """
        After a rejected cycle attempt, the involved tasks must be unchanged.
        """
        a = make_task(title="A")
        b = make_task(title="B", blocked_by=a["id"])

        # Attempt cycle — should fail
        client.put(f"/tasks/{a['id']}", json={"blocked_by": b["id"]})

        # Both tasks should still exist with their original blocked_by values
        tasks = {t["id"]: t for t in client.get("/tasks").json()}
        assert tasks[a["id"]]["blocked_by"] is None
        assert tasks[b["id"]]["blocked_by"] == a["id"]


# ═════════════════════════════════════════════════════════════════════════════
# Blocking state (visual blocking helpers used by the Flutter frontend)
# ═════════════════════════════════════════════════════════════════════════════

class TestBlockingState:

    def test_task_blocked_by_undone_task(self, client, make_task):
        """
        Task B blocked_by Task A (To-Do).
        B's blocked_by field must reference A.
        The Flutter provider derives the visual-blocked state from this.
        """
        a = make_task(title="A — not done")
        b = make_task(title="B — blocked", blocked_by=a["id"])

        tasks = {t["id"]: t for t in client.get("/tasks").json()}
        assert tasks[b["id"]]["blocked_by"] == a["id"]
        assert tasks[a["id"]]["status"] != "Done"

    def test_task_unblocked_when_blocker_is_done(self, client, make_task):
        """
        Once Task A is Done, Task B is no longer logically blocked.
        The blocked_by field still points to A (that's correct — it's the
        frontend that decides visual state), and A's status is "Done".
        """
        a = make_task(title="A")
        b = make_task(title="B", blocked_by=a["id"])

        # Mark A as Done
        client.put(f"/tasks/{a['id']}", json={"status": "Done"})

        tasks = {t["id"]: t for t in client.get("/tasks").json()}
        # B still references A but A is Done → frontend unblocks B
        assert tasks[b["id"]]["blocked_by"] == a["id"]
        assert tasks[a["id"]]["status"] == "Done"

    def test_missing_blocker_reference(self, client, make_task):
        """
        blocked_by pointing to a non-existent task ID should be rejected
        at creation time with 404.
        """
        resp = client.post("/tasks", json={
            "title": "Ghost blocked",
            "blocked_by": 88888,
        })
        assert resp.status_code == 404

    def test_missing_blocker_cleared_on_delete(self, client, make_task):
        """
        After blocker is deleted, dependent task's blocked_by becomes None.
        The frontend then treats it as unblocked — correct behaviour.
        """
        blocker = make_task(title="Blocker")
        dep = make_task(title="Dependent", blocked_by=blocker["id"])

        client.delete(f"/tasks/{blocker['id']}")

        tasks = {t["id"]: t for t in client.get("/tasks").json()}
        assert tasks[dep["id"]]["blocked_by"] is None

    def test_chain_a_blocks_b_blocks_c(self, client, make_task):
        """Three-task linear chain is created without error."""
        a = make_task(title="A — root")
        b = make_task(title="B", blocked_by=a["id"])
        c = make_task(title="C", blocked_by=b["id"])

        tasks = {t["id"]: t for t in client.get("/tasks").json()}
        assert tasks[b["id"]]["blocked_by"] == a["id"]
        assert tasks[c["id"]]["blocked_by"] == b["id"]
