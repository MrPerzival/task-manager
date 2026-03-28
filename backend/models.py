"""
models.py
---------
SQLAlchemy ORM table definitions.
Mirrors the Pydantic schemas exactly so backend ↔ frontend data contracts match.
"""

from sqlalchemy import Column, Integer, String, Date, Enum as SAEnum
from database import Base
import enum


class StatusEnum(str, enum.Enum):
    todo = "To-Do"
    in_progress = "In Progress"
    done = "Done"


class RecurringEnum(str, enum.Enum):
    none = "None"
    daily = "Daily"
    weekly = "Weekly"


class Task(Base):
    __tablename__ = "tasks"

    id          = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title       = Column(String(255), nullable=False)
    description = Column(String(2000), nullable=False, default="")
    due_date    = Column(Date, nullable=True)
    status      = Column(
        SAEnum("To-Do", "In Progress", "Done", name="status_enum"),
        nullable=False,
        default="To-Do",
    )
    blocked_by  = Column(Integer, nullable=True)   # FK-like; kept loose to avoid cascade complexity
    recurring   = Column(
        SAEnum("None", "Daily", "Weekly", name="recurring_enum"),
        nullable=False,
        default="None",
    )
