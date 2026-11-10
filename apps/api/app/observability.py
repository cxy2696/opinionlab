"""Structured JSON logging, trace propagation and Prometheus metrics ()."""

from __future__ import annotations

import contextvars
import io
import logging
import logging.handlers
import re
import time
import uuid
from collections.abc import Iterator, MutableMapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import structlog
from prometheus_client import Counter, Gauge, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="")
org_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("org_id", default="")
user_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("user_id", default="")

EMAIL_RE = re.compile(r"^([^@]{1,2})[^@]*(@.*)$")


def mask_email(email: str) -> str:
    match = EMAIL_RE.match(email)
    if not match:
        return "***"
    return f"{match.group(1)}***{match.group(2)}"


def mask_hmac(value: str) -> str:
    return f"{value[:8]}…" if len(value) > 8 else value


def truncate(value: str, limit: int = 200) -> str:
    return value if len(value) <= limit else value[:limit] + "…"


def _masking_processor(
    logger: Any, method_name: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    for key in ("email", "user_email", "actor_email"):
        if isinstance(event_dict.get(key), str):
            event_dict[key] = mask_email(event_dict[key])
    for key in ("hmac", "pseudonym", "hmac_value"):
        if isinstance(event_dict.get(key), str):
            event_dict[key] = mask_hmac(event_dict[key])
    if isinstance(event_dict.get("description"), str):
        event_dict["description"] = truncate(event_dict["description"])
    event_dict.setdefault("trace_id", trace_id_var.get())
    event_dict.setdefault("org_id", org_id_var.get())
    event_dict.setdefault("user_id", user_id_var.get())
    if "timestamp" not in event_dict:
        event_dict["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return event_dict


def configure_logging(stream: Any = None, level: int = logging.INFO) -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            _masking_processor,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(file=stream or io.StringIO()),
        cache_logger_on_first_use=False,
    )


def get_logger() -> Any:
    return structlog.get_logger("opinionlab")


def build_file_handler(path: str | Path) -> logging.Handler:
    """Daily rotation with 7-day retention."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.TimedRotatingFileHandler(
        target, when="midnight", backupCount=7, encoding="utf-8"
    )
    return handler


@contextmanager
def temporary_debug(seconds: float = 60.0) -> Iterator[None]:
    """Temporarily enable DEBUG and restore automatically."""
    import threading

    previous = logging.getLogger().level
    logging.getLogger().setLevel(logging.DEBUG)
    timer = threading.Timer(seconds, lambda: logging.getLogger().setLevel(previous))
    timer.daemon = True
    timer.start()
    try:
        yield
    finally:
        timer.cancel()
        logging.getLogger().setLevel(previous)


API_DURATION = Histogram(
    "opinionlab_api_duration_seconds",
    "API request duration",
    ["method", "path", "status"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0),
)
QUEUE_DEPTH = Gauge("opinionlab_queue_depth", "Celery queue depth", ["queue"])
JOB_DURATION = Histogram(
    "opinionlab_job_duration_seconds",
    "Simulation job duration",
    buckets=(1, 5, 15, 60, 300, 900, 3600),
)
REPLICA_FAILURE = Counter(
    "opinionlab_replica_failures_total", "Failed replicas", ["reason"]
)
CONNECTOR_STATE = Gauge(
    "opinionlab_connector_circuit_state",
    "Connector breaker state (0 closed, 1 half-open, 2 open)",
    ["site"],
)


def _labels_from_request(request: Request) -> tuple[str, str]:
    org = org_id_var.get()
    user = user_id_var.get()
    authorization = request.headers.get("Authorization", "")
    if authorization.startswith("Bearer ") and not (org or user):
        from app.security import decode_token

        try:
            payload = decode_token(authorization[7:], "access")
            org, user = str(payload.get("org_id", "")), str(payload.get("sub", ""))
        except ValueError:
            pass
    return org, user


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Any) -> Response:
        trace_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.trace_id = trace_id
        trace_token = trace_id_var.set(trace_id)
        org, user = _labels_from_request(request)
        org_token = org_id_var.set(org)
        user_token = user_id_var.set(user)
        started = time.perf_counter()
        status = 500
        error_detail = ""
        try:
            response: Response = await call_next(request)
            status = response.status_code
            response.headers["X-Request-ID"] = trace_id
        except Exception as exc:  # pragma: no cover - re-raised after logging
            error_detail = type(exc).__name__
            raise
        finally:
            duration_ms = (time.perf_counter() - started) * 1000.0
            route = request.scope.get("route")
            path = getattr(route, "path", request.url.path)
            API_DURATION.labels(request.method, path, str(status)).observe(duration_ms / 1000.0)
            get_logger().info(
                "http_request",
                action=f"{request.method} {path}",
                duration_ms=round(duration_ms, 3),
                status=status,
                error_detail=error_detail,
                extra={"client_ip": request.client.host if request.client else ""},
            )
            trace_id_var.reset(trace_token)
            org_id_var.reset(org_token)
            user_id_var.reset(user_token)
        return response


def bind_trace_from_headers(headers: dict[str, str] | None) -> str:
    """Celery workers inherit the producer's trace id."""
    trace_id = (headers or {}).get("trace_id") or str(uuid.uuid4())
    trace_id_var.set(trace_id)
    return trace_id


def metrics_payload() -> tuple[bytes, str]:
    return generate_latest(), "text/plain; version=0.0.4; charset=utf-8"
