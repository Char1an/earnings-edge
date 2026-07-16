.PHONY: help db-up db-down db-logs install migrate universe backfill api

help:
	@echo "db-up       start Postgres via docker compose"
	@echo "db-down     stop Postgres"
	@echo "db-logs     tail Postgres logs"
	@echo "install     create venv and install backend deps"
	@echo "migrate     run alembic migrations to head"
	@echo "universe    load Nifty 500 constituents into stocks table"
	@echo "backfill    backfill 10y OHLCV for Nifty 500"
	@echo "api         run FastAPI dev server"

db-up:
	docker compose up -d

db-down:
	docker compose down

db-logs:
	docker compose logs -f postgres

install:
	cd backend && python3.11 -m venv .venv && . .venv/bin/activate && pip install -U pip && pip install -e ".[dev]"

migrate:
	cd backend && . .venv/bin/activate && alembic upgrade head

universe:
	cd backend && . .venv/bin/activate && python -m ingest.sources.nse_universe

backfill:
	cd backend && . .venv/bin/activate && python -m ingest.sources.nse_prices --mode backfill --years 10

api:
	cd backend && . .venv/bin/activate && uvicorn app.main:app --reload
