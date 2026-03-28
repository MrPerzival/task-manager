"""
database.py
-----------
SQLAlchemy engine + session factory + declarative Base.

Environment-aware:
  • Reads DATABASE_URL from the environment (or a .env file via python-dotenv).
  • Falls back to a local SQLite file for zero-config local development.
  • Enables connection-pool health checks (pool_pre_ping) for PostgreSQL
    so stale connections are automatically discarded after a DB restart.
  • connect_args={"check_same_thread": False} is only applied for SQLite
    because that flag is unknown to psycopg2 and would crash at startup.
"""

import os
import logging

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ── Load .env file (no-op when the file is absent — safe for production) ──────
load_dotenv()

logger = logging.getLogger(__name__)

# ── Resolve DATABASE_URL ──────────────────────────────────────────────────────
# Priority: real environment variable → .env file value → SQLite fallback
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./tasks.db")

_is_sqlite = DATABASE_URL.startswith("sqlite")

if _is_sqlite:
    logger.info("Database backend: SQLite  (%s)", DATABASE_URL)
else:
    # Mask credentials in the log line
    _safe_url = DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL
    logger.info("Database backend: PostgreSQL  (…@%s)", _safe_url)

# ── Engine ────────────────────────────────────────────────────────────────────
# pool_pre_ping:
#   Before each pooled connection is handed to a route, SQLAlchemy emits a
#   cheap probe query (SELECT 1).  Stale connections (e.g. after a DB
#   restart) are detected and replaced transparently — critical for
#   long-lived production deployments on Render / Docker.
#
# connect_args:
#   check_same_thread=False  → SQLite only; lets multiple FastAPI worker
#   threads share one connection.  Must NOT be passed to psycopg2.
#
# pool_size / max_overflow / pool_recycle:
#   PostgreSQL only; keep a healthy, bounded connection pool and recycle
#   connections before hitting the server's idle-timeout (typically 10 min).

_engine_kwargs: dict = {"pool_pre_ping": True}

if _is_sqlite:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    _engine_kwargs["pool_size"]    = 5
    _engine_kwargs["max_overflow"] = 10
    _engine_kwargs["pool_recycle"] = 1800  # 30 minutes

engine = create_engine(DATABASE_URL, **_engine_kwargs)

# ── Session factory ───────────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# ── Declarative Base shared by all ORM models ─────────────────────────────────
Base = declarative_base()


# ── FastAPI session dependency ────────────────────────────────────────────────
def get_db():
    """
    Yields a scoped DB session and guarantees cleanup regardless of outcome.
    Rolls back on any unhandled exception so the connection returns to the
    pool in a clean state.

    Usage::

        @app.get("/tasks")
        def list_tasks(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
