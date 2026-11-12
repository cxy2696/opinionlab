"""compose topology, non-root images, dual-region values and CI jobs."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]


def _compose() -> dict[str, object]:
    return yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))


def test_compose_contains_required_services_and_healthchecks() -> None:
    compose = _compose()
    services = compose["services"]
    assert {"db", "redis", "minio", "api", "worker"} <= set(services)
    for name in ("db", "redis", "minio", "api"):
        assert "healthcheck" in services[name], name
        assert services[name]["restart"] == "unless-stopped"
    api_deps = services["api"]["depends_on"]
    assert api_deps["db"]["condition"] == "service_healthy"
    assert api_deps["redis"]["condition"] == "service_healthy"
    assert api_deps["minio"]["condition"] == "service_healthy"


def test_worker_resource_limits_and_no_localhost_for_app_services() -> None:
    services = _compose()["services"]
    limits = services["worker"]["deploy"]["resources"]["limits"]
    assert str(limits["cpus"]) == "8"
    assert limits["memory"] == "16G"
    for name in ("api", "worker"):
        env = services[name]["environment"]
        assert "localhost" not in str(env["DATABASE_URL"])
        assert "localhost" not in str(env["REDIS_URL"])
        assert "@db:5432" in env["DATABASE_URL"]
        assert "redis:6379" in env["REDIS_URL"]


def test_env_example_and_optional_compose_env() -> None:
    sample = (ROOT / ".env.example").read_text(encoding="utf-8")
    for key in ("DATABASE_URL", "REDIS_URL", "JWT_SECRET", "OLLAMA_ENABLED", "DEMO_MAX_NODES"):
        assert key in sample
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "!.env.example" in gitignore
    compose = _compose()["services"]
    for name in ("api", "worker"):
        env_file = compose[name]["env_file"]
        assert env_file == [{"path": ".env", "required": False}], name
    worker_deps = compose["worker"]["depends_on"]
    assert worker_deps["minio"]["condition"] == "service_healthy"

    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    assert ".env" in dockerignore and ".git" in dockerignore


def test_dockerfiles_pin_digest_and_run_as_non_root() -> None:
    for name in ("api.Dockerfile", "worker.Dockerfile"):
        text = (ROOT / "deploy" / "docker" / name).read_text(encoding="utf-8")
        assert re.search(r"FROM python:3\.12\.\d+-slim-bookworm@sha256:[0-9a-f]{64}", text), name
        assert "USER app" in text
        assert "useradd" in text


def test_private_offline_and_dual_region_values() -> None:
    offline = (ROOT / "deploy" / "private" / "OFFLINE.md").read_text(encoding="utf-8")
    assert "Load images" in offline
    assert "air-gapped" in offline.lower()

    cn = yaml.safe_load((ROOT / "deploy" / "k8s" / "helm-cn" / "values.yaml").read_text())
    eu = yaml.safe_load((ROOT / "deploy" / "k8s" / "helm-global" / "values.yaml").read_text())
    assert cn["region"] == "cn" and eu["region"] == "global"
    assert cn["domain"] != eu["domain"]
    assert cn["storage"]["bucket"] != eu["storage"]["bucket"]
    assert cn["secrets"]["hmacSaltSecretName"] != eu["secrets"]["hmacSaltSecretName"]
    assert cn["secrets"]["jwtSecretName"] != eu["secrets"]["jwtSecretName"]


def test_ci_has_migration_and_weekly_audit() -> None:
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "migrate:" in ci
    assert "alembic upgrade head" in ci
    security = (ROOT / ".github" / "workflows" / "security.yml").read_text(encoding="utf-8")
    assert "schedule:" in security
    assert "cron:" in security
    assert "pip-audit" in security
    assert "uv lock --check" in ci
    assert "uv sync --locked" in ci
    assert "uv sync --locked" in security


def test_pages_workflow_tracks_shared_ui_and_scenarios() -> None:
    pages = (ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
    for marker in (
        "apps/web/**",
        "scenarios/**",
        "scripts/build_site.py",
        "scripts/build_static_templates.py",
        "uv sync --locked",
        "uv run --no-sync python scripts/build_static_templates.py",
    ):
        assert marker in pages


def test_runbook_documents_canary_rollback_and_tainted() -> None:
    text = (ROOT / "docs" / "RUNBOOK.md").read_text(encoding="utf-8")
    assert "Canary" in text
    assert "rollback" in text.lower()
    assert "tainted" in text.lower()
    assert "spec_sha256" in text


def test_single_container_demo_is_database_free_and_non_root() -> None:
    compose = yaml.safe_load((ROOT / "docker-compose.demo.yml").read_text(encoding="utf-8"))
    services = compose["services"]
    assert set(services) == {"demo"}
    assert "depends_on" not in services["demo"]
    assert services["demo"]["build"]["dockerfile"] == "deploy/docker/demo.Dockerfile"
    assert "healthcheck" in services["demo"]
    environment = services["demo"]["environment"]
    assert "DATABASE_URL" not in environment
    assert "REDIS_URL" not in environment
    assert environment["DEMO_MAX_REPEATS"] == "${DEMO_MAX_REPEATS:-20}"

    text = (ROOT / "deploy" / "docker" / "demo.Dockerfile").read_text(encoding="utf-8")
    assert re.search(r"FROM python:3\.12\.\d+-slim-bookworm@sha256:[0-9a-f]{64}", text)
    assert "USER app" in text
    assert "alembic" not in text
    assert "HEALTHCHECK" in text
