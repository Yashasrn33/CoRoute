# CoRoute dev commands. Backend uses uv; run DB (Postgres) locally on :5432.
.PHONY: help dev api migrate revision test lint seed db-roles

help:
	@echo "make api       - run the FastAPI backend (uvicorn, reload)"
	@echo "make migrate   - apply Alembic migrations"
	@echo "make revision  - create a new Alembic revision (m='message')"
	@echo "make test      - run backend tests (incl. privacy invariants)"
	@echo "make lint      - ruff + mypy"
	@echo "make seed      - seed the World Cup demo data (TODO: seed script)"
	@echo "make db-roles  - create local Postgres roles + database"

api:
	cd backend && uv run uvicorn app.main:app --reload --port 8000

migrate:
	cd backend && uv run alembic upgrade head

revision:
	cd backend && uv run alembic revision -m "$(m)"

test:
	cd backend && uv run pytest -q

lint:
	cd backend && uv run ruff check . && uv run mypy app

seed:
	cd backend && uv run python -m app.seed

# One-time local DB bootstrap (idempotent). Requires a running Postgres you can
# administer as a superuser (peer auth on the unix socket).
db-roles:
	psql -d postgres -v ON_ERROR_STOP=1 -f scripts/roles.sql
	psql -d postgres -tc "SELECT 1 FROM pg_database WHERE datname='coroute'" | grep -q 1 || createdb -O coroute_owner coroute
