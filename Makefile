.DEFAULT_GOAL := check

PYTEST := uv run pytest

.PHONY: setup test check bench

setup:
	uv sync
	@if command -v docker >/dev/null 2>&1; then docker compose up -d db redis minio || echo "docker compose unavailable or not running; skipped"; fi

test:
	uv run pytest

check:
	uv run ruff check .
	uv run mypy
	uv run pytest

bench:
	uv run pytest benchmarks -q
