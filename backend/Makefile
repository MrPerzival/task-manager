# Makefile — Task Manager Backend
# ─────────────────────────────────────────────────────────────────────────────
# All targets run from the backend/ directory.
# Run `make help` to see available commands.
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: help install dev test test-cov lint format \
        migrate migrate-create migrate-rollback \
        docker-up docker-down docker-logs docker-rebuild \
        clean

# ── Colours for help output ───────────────────────────────────────────────────
BOLD  := \033[1m
RESET := \033[0m
CYAN  := \033[36m

# ── Python / Uvicorn config ───────────────────────────────────────────────────
PYTHON     := python3
PIP        := pip
APP        := main:app
HOST       := 0.0.0.0
PORT       := 8000

# ─────────────────────────────────────────────────────────────────────────────

help:   ## Show this help message
	@echo ""
	@echo "$(BOLD)Task Manager — Backend Makefile$(RESET)"
	@echo "─────────────────────────────────────────────────"
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*?##/ \
		{ printf "  $(CYAN)%-22s$(RESET) %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@echo ""

# ── Setup ─────────────────────────────────────────────────────────────────────

install:  ## Install all production dependencies
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

install-dev:  ## Install production + development/testing dependencies
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install pytest pytest-asyncio httpx ruff black

# ── Run ───────────────────────────────────────────────────────────────────────

dev:  ## Start the dev server with hot-reload (SQLite fallback)
	uvicorn $(APP) --host $(HOST) --port $(PORT) --reload

start:  ## Start the production server (no reload)
	uvicorn $(APP) --host $(HOST) --port $(PORT)

start-render:  ## Start on Render's required port 10000
	uvicorn $(APP) --host 0.0.0.0 --port 10000

# ── Tests ─────────────────────────────────────────────────────────────────────

test:  ## Run the full test suite (SQLite in-memory)
	DATABASE_URL="sqlite:///:memory:" pytest

test-v:  ## Run tests with verbose output
	DATABASE_URL="sqlite:///:memory:" pytest -v

test-cov:  ## Run tests with HTML coverage report (requires pytest-cov)
	DATABASE_URL="sqlite:///:memory:" \
		pytest --cov=. --cov-report=html --cov-report=term-missing \
		--cov-omit="tests/*,alembic/*"
	@echo "Coverage report → htmlcov/index.html"

test-fast:  ## Run tests, stop on first failure
	DATABASE_URL="sqlite:///:memory:" pytest -x

test-watch:  ## Re-run tests on file change (requires pytest-watch)
	DATABASE_URL="sqlite:///:memory:" ptw -- --tb=short

# ── Linting & formatting ──────────────────────────────────────────────────────

lint:  ## Run ruff linter
	ruff check . --select E,F,W,I --ignore E501

lint-fix:  ## Run ruff linter and auto-fix safe issues
	ruff check . --select E,F,W,I --ignore E501 --fix

format:  ## Format code with black
	black .

format-check:  ## Check formatting without modifying files
	black --check --diff .

# ── Database migrations (Alembic) ─────────────────────────────────────────────

migrate:  ## Apply all pending migrations (upgrade head)
	alembic upgrade head

migrate-create:  ## Create a new migration  (use: make migrate-create MSG="add column foo")
	@if [ -z "$(MSG)" ]; then \
		echo "Usage: make migrate-create MSG=\"description\""; exit 1; \
	fi
	alembic revision --autogenerate -m "$(MSG)"

migrate-rollback:  ## Roll back one migration
	alembic downgrade -1

migrate-history:  ## Show migration history
	alembic history --verbose

migrate-status:  ## Show current migration revision
	alembic current

migrate-sql:  ## Generate SQL for pending migrations (offline mode)
	alembic upgrade head --sql

# ── Docker ────────────────────────────────────────────────────────────────────

docker-up:  ## Start the full stack (API + PostgreSQL) in detached mode
	docker compose up --build -d
	@echo "API  →  http://localhost:8000"
	@echo "Docs →  http://localhost:8000/docs"

docker-down:  ## Stop and remove containers (preserves the DB volume)
	docker compose down

docker-clean:  ## Stop containers AND wipe the database volume
	docker compose down -v
	@echo "Database volume removed."

docker-logs:  ## Tail logs from the API container
	docker compose logs -f api

docker-rebuild:  ## Force-rebuild the API image and restart
	docker compose up --build --force-recreate api

docker-shell:  ## Open a shell inside the running API container
	docker compose exec api /bin/bash

docker-psql:  ## Open psql inside the running DB container
	docker compose exec db psql -U taskuser -d taskdb

# ── Utilities ─────────────────────────────────────────────────────────────────

env:  ## Copy .env.example → .env (skips if .env already exists)
	@if [ -f .env ]; then \
		echo ".env already exists — skipping."; \
	else \
		cp .env.example .env; \
		echo ".env created from .env.example. Fill in your values."; \
	fi

clean:  ## Remove Python cache files and test artefacts
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "*.pyo" -delete 2>/dev/null || true
	rm -rf .pytest_cache htmlcov .ruff_cache
	@echo "Cleaned."
