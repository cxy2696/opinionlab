"""Public, rate-limited demo application (no account required).

This is a deliberately capped surface: small graphs, few replicas and a short
horizon so the page stays responsive. Every response carries the same
"simulation, not prediction" disclaimer as the full product.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.errors import ApiError
from hnle.io.export import series_frame
from hnle.io.report import DISCLAIMERS, echarts_bundle, render_report
from hnle.mc import run_monte_carlo
from hnle.metrics import summarize
from hnle.spec import ModelSpec
from hnle.templates import Template, iter_templates

router = APIRouter(prefix="/api/v1/demo", tags=["demo"])
REPO_ROOT = Path(__file__).resolve().parents[3]
WEB_DIR = REPO_ROOT / "apps" / "web"

DEMO_MAX_NODES = 400
DEMO_MAX_STEPS = 200
DEMO_MAX_REPEATS = 20


class DemoRequest(BaseModel):
    template_key: str = "S2"
    q: float | None = Field(default=None, ge=0.01, le=20)
    latency_mu: float | None = Field(default=None, gt=0, le=120)
    repeats: int = Field(default=8, ge=1, le=DEMO_MAX_REPEATS)
    seed: int = Field(default=42, ge=0, le=1_000_000)
    steps: int | None = Field(default=None, ge=10, le=DEMO_MAX_STEPS)


def _template(key: str) -> Template:
    for template in iter_templates(REPO_ROOT / "scenarios"):
        if template.key == key and template.is_enabled():
            return template
    raise ValueError(f"unknown or disabled template: {key}")


def _variant(spec: ModelSpec, request: DemoRequest) -> ModelSpec:
    payload = spec.model_dump(mode="json")
    if request.q is not None:
        payload["q"] = request.q
    if request.latency_mu is not None:
        payload.setdefault("latency", {})["mu"] = request.latency_mu
    payload["n_steps"] = min(int(payload.get("n_steps", 100)), request.steps or DEMO_MAX_STEPS)
    payload["seed"] = request.seed
    payload["repeats"] = request.repeats
    return ModelSpec.model_validate(payload)


def _run(template: Template, request: DemoRequest) -> tuple[ModelSpec, Any, Any, Any]:
    spec = _variant(template.spec, request)
    graph = template.graph
    if graph.n_nodes > DEMO_MAX_NODES:
        # demo graphs are already small; this guard documents the cap
        raise ValueError("demo graph exceeds the node cap")
    aggregate = run_monte_carlo(spec, graph, repeats=spec.repeats, jobs=1, collect_raw=True)
    assert aggregate.raw is not None
    return spec, graph, aggregate, aggregate.raw[0]


@router.get("/templates")
async def demo_templates() -> dict[str, Any]:
    templates = [
        {
            "key": template.key,
            "name_zh": template.name_zh,
            "name_en": template.name_en,
            "question_zh": template.question_zh,
            "question_en": template.question_en,
            "assumptions_zh": template.assumptions_zh,
            "assumptions_en": template.assumptions_en,
            "limitations_zh": template.limitations_zh,
            "limitations_en": template.limitations_en,
            "defaults": {
                "q": template.spec.q,
                "latency_mu": template.spec.latency.mu,
                "n_steps": template.spec.n_steps,
                "repeats": template.spec.repeats,
            },
        }
        for template in iter_templates(REPO_ROOT / "scenarios")
        if template.is_enabled()
    ]
    return {"data": templates, "disclaimer_key": "simulation_not_prediction"}


@router.post("/simulate")
async def demo_simulate(request: DemoRequest) -> dict[str, Any]:
    try:
        template = _template(request.template_key)
    except ValueError as exc:
        raise ApiError(404, "TEMPLATE_NOT_FOUND", str(exc)) from exc
    spec, graph, aggregate, result = _run(template, request)
    summary = summarize(result, spec, graph.hyperedges).to_dict()
    frame = series_frame(result)
    return {
        "data": {
            "template": {
                "key": template.key,
                "name_zh": template.name_zh,
                "name_en": template.name_en,
                "question_zh": template.question_zh,
                "question_en": template.question_en,
            },
            "spec": {
                "q": spec.q,
                "n_steps": spec.n_steps,
                "repeats": spec.repeats,
                "seed": spec.seed,
            },
            "metrics": {
                name: {
                    "mean": item.mean,
                    "ci95_lo": item.ci95_lo,
                    "ci95_hi": item.ci95_hi,
                    "n": item.n,
                }
                for name, item in aggregate.metrics.items()
            },
            "summary": summary,
            "series": {
                "steps": frame["step"].tolist(),
                "diversity": frame["diversity"].tolist(),
                "cascade": frame["cascade"].tolist(),
            },
            "disclaimer": DISCLAIMERS["simulation_not_prediction"],
            "disclaimer_key": "simulation_not_prediction",
        }
    }


@router.post("/report", response_class=HTMLResponse)
async def demo_report(request: DemoRequest) -> HTMLResponse:
    template = _template(request.template_key)
    spec, graph, aggregate, result = _run(template, request)
    summary = summarize(result, spec, graph.hyperedges).to_dict()
    frame = series_frame(result)
    manifest = {
        "run_id": f"demo-{spec.config_sha256()[:12]}-{spec.seed}",
        "mode": "public-demo",
        "disclaimer_key": "simulation_not_prediction",
    }
    html = render_report(
        run_id=str(manifest["run_id"]),
        spec=spec,
        summary=summary,
        frame=frame,
        manifest=manifest,
        aggregate=aggregate,
        narrative={
            "assumptions_zh": template.assumptions_zh,
            "assumptions_en": template.assumptions_en,
            "limitations_zh": template.limitations_zh,
            "limitations_en": template.limitations_en,
        },
    )
    return HTMLResponse(content=html)


@router.get("/app", response_class=HTMLResponse)
async def demo_app() -> HTMLResponse:
    return HTMLResponse(content=(WEB_DIR / "index.html").read_text(encoding="utf-8"))


@router.get("/echarts.js")
async def demo_app_echarts() -> Any:
    from fastapi.responses import Response

    return Response(content=echarts_bundle(), media_type="application/javascript")
