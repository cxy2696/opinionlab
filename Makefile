.DEFAULT_GOAL := check

PYTEST := uv run pytest

.PHONY: setup test check bench migrate demo site case

setup:
	uv sync
	@if command -v docker >/dev/null 2>&1; then docker compose up -d db redis minio || echo "docker compose unavailable or not running; skipped"; fi

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

site:
	python scripts/build_site.py

bench:
	uv run pytest benchmarks -q

case:
	uv run python examples/kaggle_hashtag_case.py
