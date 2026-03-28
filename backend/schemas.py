"""
schemas.py
----------
Pydantic v2 schemas for request validation and response serialization.
All three (create / update / response) use the same field definitions
so the Flutter client receives a consistent shape.
"""

from datetime import date
from typing import Literal, Optional
from pydantic import BaseModel, field_validator


# ── Shared field types ────────────────────────────────────────────────────────
StatusType    = Literal["To-Do", "In Progress", "Done"]
RecurringType = Literal["None", "Daily", "Weekly"]


# ── Request: Create ───────────────────────────────────────────────────────────
class TaskCreate(BaseModel):
    title:       str
    description: str = ""
    due_date:    Optional[date] = None
    status:      StatusType = "To-Do"
    blocked_by:  Optional[int] = None
    recurring:   RecurringType = "None"

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Title must not be empty.")
        return v.strip()


# ── Request: Update (all fields optional) ────────────────────────────────────
class TaskUpdate(BaseModel):
    title:       Optional[str] = None
    description: Optional[str] = None
    due_date:    Optional[date] = None
    status:      Optional[StatusType] = None
    blocked_by:  Optional[int] = None
    recurring:   Optional[RecurringType] = None

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Title must not be empty.")
        return v.strip() if v else v


# ── Response ──────────────────────────────────────────────────────────────────
class TaskResponse(BaseModel):
    id:          int
    title:       str
    description: str
    due_date:    Optional[date]
    status:      str
    blocked_by:  Optional[int]
    recurring:   str

    model_config = {"from_attributes": True}
