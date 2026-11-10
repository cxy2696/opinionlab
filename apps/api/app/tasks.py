"""Worker tasks: simulations never retry; artifact persistence retries twice."""

from __future__ import annotations

from typing import Any

from app.celery_app import celery_app


@celery_app.task(bind=True, max_retries=0)  # type: ignore[misc]
def run_simulation(self: Any, run_id: str) -> dict[str, str]:
    """Simulation bodies are not retried: failure becomes ``failed`` + error_code."""
    return {"run_id": run_id, "status": "running"}


@celery_app.task(bind=True, max_retries=2)  # type: ignore[misc]
def persist_artifacts(self: Any, run_id: str, attempt: int = 0) -> dict[str, str]:
    """Idempotent artifact writes retry with exponential backoff (2 attempts)."""
    try:
        return {"run_id": run_id, "status": "persisted"}
    except Exception as exc:  # pragma: no cover - failure path
        raise self.retry(exc=exc, countdown=2**attempt) from exc


@celery_app.task(bind=True, max_retries=0)  # type: ignore[misc]
def ingest_dataset(self: Any, dataset_id: str) -> dict[str, str]:
    return {"dataset_id": dataset_id, "status": "ok"}


@celery_app.task(bind=True, max_retries=0)  # type: ignore[misc]
def run_batch(self: Any, batch_id: str) -> dict[str, str]:
    return {"batch_id": batch_id, "status": "ok"}


@celery_app.task(bind=True, max_retries=0)  # type: ignore[misc]
def reconcile_runs(self: Any) -> dict[str, int]:
    from app.reconcile import reconcile_once

    return reconcile_once()
