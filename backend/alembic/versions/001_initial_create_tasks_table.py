"""Initial migration — create tasks table

Revision ID: 001_initial
Revises:
Create Date: 2025-01-01 00:00:00.000000

This migration creates the `tasks` table with all columns defined in the
v1 data model.  It is database-agnostic: the SA Enum type renders as a
native PostgreSQL ENUM in PG and as a VARCHAR CHECK constraint in SQLite.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the tasks table."""
    op.create_table(
        "tasks",
        sa.Column("id",          sa.Integer(),    nullable=False, autoincrement=True),
        sa.Column("title",       sa.String(255),  nullable=False),
        sa.Column("description", sa.String(2000), nullable=False, server_default=""),
        sa.Column(
            "due_date",
            sa.Date(),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.Enum("To-Do", "In Progress", "Done", name="status_enum"),
            nullable=False,
            server_default="To-Do",
        ),
        sa.Column("blocked_by", sa.Integer(), nullable=True),
        sa.Column(
            "recurring",
            sa.Enum("None", "Daily", "Weekly", name="recurring_enum"),
            nullable=False,
            server_default="None",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tasks_id", "tasks", ["id"], unique=False)


def downgrade() -> None:
    """Drop the tasks table and its associated enums."""
    op.drop_index("ix_tasks_id", table_name="tasks")
    op.drop_table("tasks")

    # Drop PostgreSQL native ENUM types if they exist.
    # bind().dialect.name check ensures this only runs on PostgreSQL.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        sa.Enum(name="status_enum").drop(bind, checkfirst=True)
        sa.Enum(name="recurring_enum").drop(bind, checkfirst=True)
