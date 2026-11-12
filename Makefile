.DEFAULT_GOAL := check

PYTEST := uv run pytest

.PHONY: setup test check bench migrate demo demo-container site case

setup:
	@if [ ! -f .env ]; then cp .env.example .env; echo "created .env from .env.example (local development defaults)"; fi
	uv sync
	@if command -v docker >/dev/null 2>&1; then \
		docker compose up -d --wait db redis minio && uv run alembic upgrade head || \
		echo "docker compose or the database is unavailable; skipped local infrastructure"; \
	else \
		echo "docker not found; skipped local database, Redis and MinIO"; \
	fi

test:
	uv run pytest

check:
	uv run ruff check .
	uv run mypy
	uv run pytest

migrate:
	uv run alembic upgrade head

demo:
	uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

demo-container:
	docker compose -f docker-compose.demo.yml up --build

site:
	uv run python scripts/build_site.py

bench:
	uv run pytest benchmarks -q

case:
	uv run python examples/kaggle_hashtag_case.py
