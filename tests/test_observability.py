"""JSON logs, masking, trace propagation and Prometheus metrics."""

from __future__ import annotations

import io
import json
import logging
import time
from pathlib import Path
from types import SimpleNamespace

import httpx
from app.celery_app import _bind_task_trace
from app.main import app
from app.observability import (
    bind_trace_from_headers,
    build_file_handler,
    configure_logging,
    get_logger,
    mask_email,
    mask_hmac,
    temporary_debug,
    trace_id_var,
    truncate,
)
from app.ratelimit import reset as reset_rate_limit


def test_masking_helpers() -> None:
    assert mask_email("analyst@example.com") == "an***@example.com"
    assert mask_email("not-an-email") == "***"
    long_hash = "a" * 64
    assert mask_hmac(long_hash) == "aaaaaaaa…"
    assert truncate("x" * 300) == "x" * 200 + "…"


def test_json_log_contains_required_fields_and_masks() -> None:
    stream = io.StringIO()
    configure_logging(stream=stream)
    get_logger().info(
        "login_attempt",
        email="analyst@example.com",
        hmac="abcdef0123456789",
        description="x" * 300,
        action="auth.login",
        duration_ms=3.2,
        status=200,
        error_detail="",
    )
    payload = json.loads(stream.getvalue().strip().splitlines()[-1])
    for field in (
        "timestamp",
        "level",
        "trace_id",
        "org_id",
        "user_id",
        "action",
        "duration_ms",
        "status",
        "error_detail",
    ):
        assert field in payload
    assert payload["email"] == "an***@example.com"
    assert payload["hmac"] == "abcdef01…"
    assert len(payload["description"]) <= 201


def test_trace_header_is_echoed_or_generated() -> None:
    async def run() -> tuple[str, str]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            reset_rate_limit()
            fixed = await client.get("/health", headers={"X-Request-ID": "trace-123"})
            generated = await client.get("/health")
            assert fixed.headers["X-Request-ID"] == "trace-123"
            return fixed.headers["X-Request-ID"], generated.headers["X-Request-ID"]

    fixed, generated = __import__("asyncio").run(run())
    assert fixed == "trace-123"
    assert len(generated) >= 32


def test_prometheus_metrics_endpoint() -> None:
    async def run() -> str:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            reset_rate_limit()
            await client.get("/health")
            response = await client.get("/metrics")
            assert response.status_code == 200
            return response.text

    text = __import__("asyncio").run(run())
    assert "opinionlab_api_duration_seconds" in text
    assert "opinionlab_queue_depth" in text
    assert "opinionlab_job_duration_seconds" in text
    assert "opinionlab_connector_circuit_state" in text
    assert "opinionlab_api_duration_seconds_count" in text


def test_celery_inherits_trace_id() -> None:
    bind_trace_from_headers({"trace_id": "celery-trace"})
    assert trace_id_var.get() == "celery-trace"
    task = SimpleNamespace(request=SimpleNamespace(headers={"trace_id": "task-trace"}))
    _bind_task_trace(task_id="t1", task=task)
    assert trace_id_var.get() == "task-trace"


def test_daily_rotation_keeps_seven_days(tmp_path: Path) -> None:
    handler = build_file_handler(tmp_path / "app.log")
    try:
        assert handler.backupCount == 7
        assert handler.when == "MIDNIGHT"
    finally:
        handler.close()


def test_temporary_debug_restores_level() -> None:
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    with temporary_debug(seconds=0.05):
        assert root.level == logging.DEBUG
    time.sleep(0.1)
    assert root.level == logging.INFO


def test_runbook_documents_alerts() -> None:
    text = (Path(__file__).parents[1] / "docs" / "RUNBOOK.md").read_text(encoding="utf-8")
    assert "ApiP95High" in text
    assert "QueueDepthHigh" in text
    assert "ConnectorOpen" in text
    assert "7" in text and "DEBUG" in text
