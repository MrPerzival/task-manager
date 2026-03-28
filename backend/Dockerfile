# ─────────────────────────────────────────────────────────────────────────────
# Dockerfile  —  Task Manager FastAPI Backend
# ─────────────────────────────────────────────────────────────────────────────
# Multi-stage aware single-stage build using a slim Python base image.
# Result: a lean (~150 MB), production-ready container.
#
# Build:
#   docker build -t task-manager-api .
#
# Run standalone (SQLite fallback, dev only):
#   docker run -p 8000:8000 task-manager-api
#
# Run with PostgreSQL (pass DATABASE_URL at runtime):
#   docker run -p 8000:8000 -e DATABASE_URL=postgresql://... task-manager-api
# ─────────────────────────────────────────────────────────────────────────────

# ── Base image ────────────────────────────────────────────────────────────────
# python:3.11-slim keeps the image small while including the full CPython
# runtime.  We pin the minor version for reproducibility.
FROM python:3.11-slim

# ── Metadata ──────────────────────────────────────────────────────────────────
LABEL maintainer="task-manager"
LABEL description="Task Manager FastAPI backend"
LABEL version="2.0.0"

# ── System dependencies ───────────────────────────────────────────────────────
# libpq-dev   → required by psycopg2-binary at runtime
# curl        → used for the Docker health check below
# We run apt-get in a single layer and clean up to minimise image size.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq-dev \
        curl && \
    rm -rf /var/lib/apt/lists/*

# ── Working directory ─────────────────────────────────────────────────────────
WORKDIR /app

# ── Python dependencies ───────────────────────────────────────────────────────
# Copy requirements first so Docker can cache this layer separately.
# Re-installing deps is expensive; we only invalidate this cache when
# requirements.txt actually changes.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Application source ────────────────────────────────────────────────────────
COPY . .

# ── Non-root user ─────────────────────────────────────────────────────────────
# Running as a non-root user is a security best practice.
RUN adduser --disabled-password --gecos "" appuser && \
    chown -R appuser:appuser /app
USER appuser

# ── Runtime configuration ─────────────────────────────────────────────────────
# These are defaults; override via docker run -e or docker-compose environment.
ENV LOG_LEVEL=INFO
ENV ALLOWED_ORIGINS=*
# DATABASE_URL is intentionally NOT set here — it must be supplied at runtime
# so the image is environment-agnostic.

# ── Expose port ───────────────────────────────────────────────────────────────
# Render uses port 10000 by default; we expose both and the start command
# reads PORT from the environment (defaulting to 8000 for local Docker use).
EXPOSE 8000
EXPOSE 10000

# ── Health check ──────────────────────────────────────────────────────────────
# Docker and orchestrators use this to decide whether the container is healthy.
# Hits the lightweight /  endpoint every 30 seconds.
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/ || exit 1

# ── Start command ─────────────────────────────────────────────────────────────
# PORT env var lets the same image run on Render (port 10000) and locally
# (port 8000) without changing the Dockerfile.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
