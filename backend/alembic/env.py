"""
alembic/env.py
--------------
Alembic environment script.  Runs in two modes:

offline  – generates SQL migration scripts without a live DB connection.
           Useful for DBA review or air-gapped deployments.

online   – connects to the real database and applies migrations directly.
           This is what `alembic upgrade head` does in production.

Configuration priority
----------------------
1. DATABASE_URL environment variable (set by .env, Docker, Render, etc.)
2. sqlalchemy.url in alembic.ini  (only used as a last resort / local fallback)
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

# ── Ensure the backend package is on the Python path ─────────────────────────
# Required when running `alembic` from the backend/ directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Load .env so DATABASE_URL is available ────────────────────────────────────
load_dotenv()

# ── Alembic Config object ─────────────────────────────────────────────────────
config = context.config

# ── Override sqlalchemy.url with the real DATABASE_URL ───────────────────────
database_url = os.getenv("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

# ── Set up Python logging from alembic.ini ────────────────────────────────────
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Import the metadata from our ORM models ───────────────────────────────────
# Alembic needs this to detect schema changes (autogenerate).
from database import Base  # noqa: E402
import models  # noqa: E402 — registers all ORM classes with Base.metadata

target_metadata = Base.metadata


# ═════════════════════════════════════════════════════════════════════════════
# Offline mode
# ═════════════════════════════════════════════════════════════════════════════

def run_migrations_offline() -> None:
    """
    Run migrations without establishing a database connection.
    Outputs raw SQL that can be piped to a DBA or applied manually.

    Usage::
        alembic upgrade head --sql > migration.sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Include schema comparison for column type changes
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ═════════════════════════════════════════════════════════════════════════════
# Online mode
# ═════════════════════════════════════════════════════════════════════════════

def run_migrations_online() -> None:
    """
    Run migrations against a live database connection.
    Used by `alembic upgrade head` and `alembic downgrade`.
    """
    # Build the engine from config (DATABASE_URL has already been injected above)
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # NullPool: no connection reuse during migrations
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# ── Entry point ───────────────────────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
