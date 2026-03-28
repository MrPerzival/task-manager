"""Add performance indexes on status and title

Revision ID: 002_add_indexes
Revises: 001_initial
Create Date: 2025-01-02 00:00:00.000000

Adds two non-unique indexes that speed up the most frequent query patterns:
  • ix_tasks_status  → GET /tasks?status=... filter
  • ix_tasks_title   → GET /tasks?search=... ILIKE filter

Note: ILIKE on a regular B-tree index provides limited speedup on large
datasets.  For full-text search at scale, migrate to PostgreSQL's
pg_trgm GIN index or a dedicated search service.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "002_add_indexes"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_tasks_status", "tasks", ["status"], unique=False)
    op.create_index("ix_tasks_title",  "tasks", ["title"],  unique=False)


def downgrade() -> None:
    op.drop_index("ix_tasks_title",  table_name="tasks")
    op.drop_index("ix_tasks_status", table_name="tasks")
