"""Celery queues and limits (PRD 10.4)."""

from __future__ import annotations

from celery import Celery
from kombu import Queue  # type: ignore[attr-defined]

from app.settings import settings

celery_app = Celery(
    "opinionlab",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_queues=(
        Queue("q_normal"),  # type: ignore[no-untyped-call]
        Queue("q_batch"),  # type: ignore[no-untyped-call]
        Queue("q_ingest"),  # type: ignore[no-untyped-call]
    ),
    task_routes={
        "app.tasks.run_simulation": {"queue": "q_normal"},
        "app.tasks.run_batch": {"queue": "q_batch"},
        "app.tasks.ingest_dataset": {"queue": "q_ingest"},
        "app.tasks.persist_artifacts": {"queue": "q_normal"},
        "app.tasks.reconcile_runs": {"queue": "q_batch"},
    },
    task_annotations={
        "app.tasks.run_simulation": {"soft_time_limit": 600, "time_limit": 900},
        "app.tasks.run_batch": {"soft_time_limit": 3600, "time_limit": 3900},
        "app.tasks.ingest_dataset": {"time_limit": 1200},
        "app.tasks.persist_artifacts": {"max_retries": 2},
    },
    worker_concurrency=8,
    task_default_queue="q_normal",
    beat_schedule={
        "reconcile-runs": {
            "task": "app.tasks.reconcile_runs",
            "schedule": 600.0,
        }
    },
)
