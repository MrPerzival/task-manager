"""
Task Management API — Production Backend
=========================================
FastAPI + SQLAlchemy  |  SQLite (dev) / PostgreSQL (prod)

New in this version
-------------------
• Structured logging (console + level controlled by LOG_LEVEL env var)
• Global exception handler → consistent JSON error envelope
• Configurable CORS origins via ALLOWED_ORIGINS env var
• dotenv support (python-dotenv)
• All original features kept intact:
    – CRUD operations
    – Task dependency (blocked_by) with visual-blocking support
    – Circular dependency detection (DFS)
    – Recurring task auto-spawn (Daily / Weekly)
    – 2-second async processing delay on create / update
    – Orphan-cleanup on delete
"""

# ── Standard library ──────────────────────────────────────────────────────────
import asyncio
import logging
import os
from datetime import timedelta
from typing import List, Optional

# ── Third-party ───────────────────────────────────────────────────────────────
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

# ── Local ─────────────────────────────────────────────────────────────────────
from database import Base, engine, get_db
import models as db_models
import schemas

# ═════════════════════════════════════════════════════════════════════════════
# 1.  Environment & Logging
# ═════════════════════════════════════════════════════════════════════════════

load_dotenv()  # reads .env when present; no-op in production

# LOG_LEVEL defaults to INFO; set DEBUG for verbose output during development
_log_level_name: str = os.getenv("LOG_LEVEL", "INFO").upper()
_log_level: int = getattr(logging, _log_level_name, logging.INFO)

logging.basicConfig(
    level=_log_level,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

logger = logging.getLogger("task_manager")
logger.info("Logging initialised at level %s", _log_level_name)

# ═════════════════════════════════════════════════════════════════════════════
# 2.  App initialisation
# ═════════════════════════════════════════════════════════════════════════════

# Create all tables on startup (idempotent — safe to run repeatedly)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Task Manager API",
    description=(
        "Production-ready task management with dependencies, recurring tasks, "
        "async processing, and PostgreSQL / SQLite support."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ═════════════════════════════════════════════════════════════════════════════
# 3.  CORS — configurable via environment
# ═════════════════════════════════════════════════════════════════════════════
# ALLOWED_ORIGINS accepts a comma-separated list, e.g.:
#   ALLOWED_ORIGINS=https://myapp.com,https://staging.myapp.com
# Leave unset (or set to "*") to allow all origins in development.

_raw_origins: str = os.getenv("ALLOWED_ORIGINS", "*")

if _raw_origins.strip() == "*":
    _cors_origins: List[str] = ["*"]
    logger.warning(
        "CORS is open to all origins. Set ALLOWED_ORIGINS in production."
    )
else:
    _cors_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]
    logger.info("CORS allowed origins: %s", _cors_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═════════════════════════════════════════════════════════════════════════════
# 4.  Global exception handlers
# ═════════════════════════════════════════════════════════════════════════════
# All unhandled exceptions are caught here and returned as a consistent JSON
# envelope so the Flutter client always gets { "error": true, "detail": "..." }
# instead of an HTML 500 page or an empty response.


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for any unhandled server error."""
    logger.exception(
        "Unhandled exception on %s %s", request.method, request.url.path
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "detail": "An unexpected server error occurred. Please try again later.",
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Override FastAPI's default HTTPException handler to include an `error` flag
    in the response body, making client-side detection uniform.
    """
    logger.warning(
        "HTTP %s on %s %s — %s",
        exc.status_code,
        request.method,
        request.url.path,
        exc.detail,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": True, "detail": exc.detail},
    )


# ═════════════════════════════════════════════════════════════════════════════
# 5.  Business-logic helpers  (all original logic preserved)
# ═════════════════════════════════════════════════════════════════════════════


def _detect_circular_dependency(
    task_id: int,
    blocked_by_id: int,
    db: Session,
    visited: Optional[set] = None,
) -> bool:
    """
    Depth-first search through the blocked_by chain.

    Starting at `blocked_by_id`, follow each task's own `blocked_by` link
    upward.  If `task_id` is encountered anywhere in that chain, accepting
    the proposed dependency would create a cycle (A → B → … → A).

    Parameters
    ----------
    task_id      : ID of the task being edited (the potential cycle root).
    blocked_by_id: ID of the task that would become the new blocker.
    db           : Active SQLAlchemy session.
    visited      : Tracks already-explored node IDs to prevent infinite loops
                   in pre-existing (non-circular) chains.

    Returns
    -------
    True  → circular dependency detected; the caller should reject the change.
    False → chain is clean.
    """
    if visited is None:
        visited = set()

    # Reached the root we started from → cycle confirmed
    if blocked_by_id == task_id:
        return True

    # Already explored this node in this DFS walk → no new cycle from here
    if blocked_by_id in visited:
        return False

    visited.add(blocked_by_id)

    blocker = (
        db.query(db_models.Task)
        .filter(db_models.Task.id == blocked_by_id)
        .first()
    )

    # Missing blocker means the chain ends here — no cycle possible
    if blocker is None:
        return False

    # Continue traversal only if this blocker is itself blocked by something
    if blocker.blocked_by is not None:
        return _detect_circular_dependency(task_id, blocker.blocked_by, db, visited)

    return False


def _create_recurring_task(original: db_models.Task, db: Session) -> db_models.Task:
    """
    Spawn the next occurrence of a recurring task after the original is Done.

    Rules
    -----
    • Copy all fields from `original` verbatim.
    • Reset status to "To-Do".
    • Advance due_date by +1 day (Daily) or +7 days (Weekly).
      If due_date is None the new task also has no due date.
    • The original task is left completely unchanged.

    Returns the newly created task ORM object.
    """
    delta = timedelta(days=1 if original.recurring == "Daily" else 7)
    next_due = (original.due_date + delta) if original.due_date else None

    new_task = db_models.Task(
        title=original.title,
        description=original.description,
        due_date=next_due,
        status="To-Do",
        blocked_by=original.blocked_by,
        recurring=original.recurring,
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    logger.info(
        "Recurring task spawned: new id=%d from original id=%d  (next_due=%s)",
        new_task.id,
        original.id,
        next_due,
    )
    return new_task


# ═════════════════════════════════════════════════════════════════════════════
# 6.  Routes
# ═════════════════════════════════════════════════════════════════════════════


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/", tags=["health"])
def root():
    """Lightweight liveness probe used by Render / Docker health checks."""
    return {"status": "ok", "message": "Task Manager API is running.", "version": "2.0.0"}


# ── GET /tasks ─────────────────────────────────────────────────────────────────

@app.get("/tasks", response_model=List[schemas.TaskResponse], tags=["tasks"])
async def get_tasks(
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Return all tasks, optionally filtered.

    Query parameters
    ----------------
    status : one of "To-Do", "In Progress", "Done"
    search : case-insensitive substring match against title
    """
    query = db.query(db_models.Task)

    if status:
        query = query.filter(db_models.Task.status == status)

    if search:
        query = query.filter(db_models.Task.title.ilike(f"%{search}%"))

    tasks = query.order_by(db_models.Task.id).all()
    logger.debug("GET /tasks → returned %d tasks (status=%s, search=%r)", len(tasks), status, search)
    return tasks


# ── POST /tasks ────────────────────────────────────────────────────────────────

@app.post("/tasks", response_model=schemas.TaskResponse, status_code=201, tags=["tasks"])
async def create_task(payload: schemas.TaskCreate, db: Session = Depends(get_db)):
    """
    Create a new task.

    Validations (in order)
    ----------------------
    1. Title must be non-empty after stripping whitespace  (also enforced by Pydantic).
    2. If blocked_by is set, the referenced task must exist.
    3. Self-block guard applied after DB insert (ID not known until then).

    Processing delay
    ----------------
    A deliberate 2-second async sleep simulates real-world processing latency
    (e.g. sending notifications, running workflows).  The event loop is NOT
    blocked — other requests are served normally during this wait.
    """
    # ── 2-second async processing delay ────────────────────────────────────
    # asyncio.sleep yields control back to the event loop; the UI stays
    # responsive and the Save button is disabled client-side during this wait.
    await asyncio.sleep(2)

    # ── Validate blocked_by reference ──────────────────────────────────────
    if payload.blocked_by is not None:
        blocker = (
            db.query(db_models.Task)
            .filter(db_models.Task.id == payload.blocked_by)
            .first()
        )
        if not blocker:
            raise HTTPException(
                status_code=404,
                detail=f"Blocking task with id={payload.blocked_by} does not exist.",
            )

    # ── Persist ────────────────────────────────────────────────────────────
    task = db_models.Task(
        title=payload.title,          # already stripped by Pydantic validator
        description=payload.description,
        due_date=payload.due_date,
        status=payload.status,
        blocked_by=payload.blocked_by,
        recurring=payload.recurring,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # ── Self-block guard ───────────────────────────────────────────────────
    # A task cannot block itself.  We can only check this after the commit
    # because the auto-incremented ID is not known before insertion.
    if task.blocked_by == task.id:
        logger.warning("Self-block detected for task id=%d — clearing blocked_by.", task.id)
        task.blocked_by = None
        db.commit()
        db.refresh(task)

    logger.info(
        "Task CREATED  id=%d  title=%r  status=%s  recurring=%s",
        task.id, task.title, task.status, task.recurring,
    )
    return task


# ── PUT /tasks/{task_id} ───────────────────────────────────────────────────────

@app.put("/tasks/{task_id}", response_model=schemas.TaskResponse, tags=["tasks"])
async def update_task(
    task_id: int,
    payload: schemas.TaskUpdate,
    db: Session = Depends(get_db),
):
    """
    Update an existing task (partial or full).

    Validations (in order)
    ----------------------
    1. Task must exist.
    2. Title, if provided, must be non-empty.
    3. blocked_by, if provided:
       a. Must not be the task's own ID (self-block).
       b. The referenced task must exist.
       c. Must not create a circular dependency (DFS check).

    Recurring spawn
    ---------------
    If the status transitions from anything → "Done" AND recurring ≠ "None",
    a new task occurrence is automatically created with the due_date advanced
    by +1 day (Daily) or +7 days (Weekly) and status reset to "To-Do".

    Processing delay
    ----------------
    Same 2-second async sleep as create, for consistent UX behaviour.
    """
    # ── 2-second async processing delay ────────────────────────────────────
    await asyncio.sleep(2)

    # ── Fetch task ─────────────────────────────────────────────────────────
    task = db.query(db_models.Task).filter(db_models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task id={task_id} not found.")

    # ── Validate title (if being updated) ─────────────────────────────────
    if payload.title is not None and not payload.title.strip():
        raise HTTPException(status_code=422, detail="Title must not be empty.")

    # ── Validate blocked_by (if being updated) ────────────────────────────
    if payload.blocked_by is not None:
        # (a) Self-block check
        if payload.blocked_by == task_id:
            raise HTTPException(status_code=422, detail="A task cannot block itself.")

        # (b) Blocker must exist
        blocker = (
            db.query(db_models.Task)
            .filter(db_models.Task.id == payload.blocked_by)
            .first()
        )
        if not blocker:
            raise HTTPException(
                status_code=404,
                detail=f"Blocking task with id={payload.blocked_by} does not exist.",
            )

        # (c) Circular dependency check (DFS)
        if _detect_circular_dependency(task_id, payload.blocked_by, db):
            raise HTTPException(
                status_code=422,
                detail=(
                    "Circular dependency detected. "
                    "Accepting this change would create a cycle in the task chain."
                ),
            )

    # ── Capture previous status before applying changes ────────────────────
    previous_status = task.status

    # ── Apply partial updates ──────────────────────────────────────────────
    if payload.title is not None:
        task.title = payload.title.strip()
    if payload.description is not None:
        task.description = payload.description
    if payload.due_date is not None:
        task.due_date = payload.due_date
    if payload.status is not None:
        task.status = payload.status
    if payload.blocked_by is not None:
        task.blocked_by = payload.blocked_by
    if payload.recurring is not None:
        task.recurring = payload.recurring

    db.commit()
    db.refresh(task)

    logger.info(
        "Task UPDATED  id=%d  title=%r  status=%s→%s  recurring=%s",
        task.id, task.title, previous_status, task.status, task.recurring,
    )

    # ── Recurring spawn — fires only on the Done transition ────────────────
    # Guard conditions:
    #   • The payload explicitly sets status to "Done"
    #   • The task was NOT already "Done" before this update (idempotent guard)
    #   • The task has a recurring schedule (not "None")
    if (
        payload.status == "Done"
        and previous_status != "Done"
        and task.recurring
        and task.recurring != "None"
    ):
        _create_recurring_task(task, db)

    return task


# ── DELETE /tasks/{task_id} ────────────────────────────────────────────────────

@app.delete("/tasks/{task_id}", status_code=204, tags=["tasks"])
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """
    Delete a task permanently.

    Orphan protection
    -----------------
    Any tasks that listed this task in their `blocked_by` field are updated
    to blocked_by=NULL so they are no longer incorrectly blocked after deletion.
    """
    task = db.query(db_models.Task).filter(db_models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task id={task_id} not found.")

    # Clear orphaned blocked_by references in one bulk UPDATE
    orphans_updated = (
        db.query(db_models.Task)
        .filter(db_models.Task.blocked_by == task_id)
        .update({"blocked_by": None})
    )
    if orphans_updated:
        logger.info(
            "Cleared blocked_by for %d orphaned task(s) after deleting id=%d",
            orphans_updated,
            task_id,
        )

    db.delete(task)
    db.commit()

    logger.info("Task DELETED  id=%d  title=%r", task_id, task.title)
    return None
