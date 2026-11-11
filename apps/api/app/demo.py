"""Public, rate-limited demo application (no account required).

This is a deliberately capped surface: small graphs, few replicas and a short
horizon so the page stays responsive. Every response carries the same
"simulation, not prediction" disclaimer as the full product.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.errors import ApiError
from app.ollama import OllamaError, build_prompt, generate_narration
from app.settings import settings
from hnle.decision import build_decision_brief
from hnle.io.export import series_frame
from hnle.io.report import DISCLAIMERS, echarts_bundle, render_report
from hnle.mc import run_monte_carlo
from hnle.metrics import summarize
from hnle.spec import ModelSpec
from hnle.templates import Template, iter_templates

router = APIRouter(prefix="/api/v1/demo", tags=["demo"])
REPO_ROOT = Path(__file__).resolve().parents[3]
WEB_DIR = REPO_ROOT / "apps" / "web"

DEMO_MAX_NODES = settings.demo_max_nodes
DEMO_MAX_STEPS = settings.demo_max_steps
DEMO_MAX_REPEATS = settings.demo_max_repeats


class DemoRequest(BaseModel):
    template_key: str = "S2"
    q: float | None = Field(default=None, ge=0.01, le=20)
    latency_mu: float | None = Field(default=None, gt=0, le=120)
    repeats: int = Field(default=8, ge=1, le=DEMO_MAX_REPEATS)
    seed: int = Field(default=42, ge=0, le=1_000_000)
    steps: int | None = Field(default=None, ge=10, le=DEMO_MAX_STEPS)
    lang: str = Field(default="zh", pattern="^(zh|en)$")


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
    payload["n_steps"] = min(
        int(payload.get("n_steps", 100)), request.steps or DEMO_MAX_STEPS, DEMO_MAX_STEPS
    )
    payload["seed"] = request.seed
    payload["repeats"] = request.repeats
    return ModelSpec.model_validate(payload)


def _run(template: Template, request: DemoRequest) -> tuple[ModelSpec, Any, Any, Any]:
    spec = _variant(template.spec, request)
    graph = template.graph
    if graph.n_nodes > DEMO_MAX_NODES:
        raise ApiError(400, "DEMO_LIMIT", "demo graph exceeds the node cap")
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
            "interpretation_zh": template.interpretation_zh,
            "interpretation_en": template.interpretation_en,
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
    return {
        "data": templates,
        "features": {"ollama": settings.ollama_enabled},
        "disclaimer_key": "simulation_not_prediction",
    }


def _bands(aggregate: Any) -> dict[str, list[float]]:
    assert aggregate.raw is not None
    matrix = np.asarray([result.diversity_series for result in aggregate.raw], dtype=np.float64)
    return {
        "p10": np.percentile(matrix, 10, axis=0).tolist(),
        "p50": np.percentile(matrix, 50, axis=0).tolist(),
        "p90": np.percentile(matrix, 90, axis=0).tolist(),
    }


def _metrics_payload(aggregate: Any) -> dict[str, dict[str, float | int | None]]:
    metrics: dict[str, dict[str, float | int | None]] = {
        name: {
            "mean": item.mean,
            "ci95_lo": item.ci95_lo,
            "ci95_hi": item.ci95_hi,
            "n": item.n,
        }
        for name, item in aggregate.metrics.items()
    }
    assert aggregate.raw is not None
    reached = [r.time_to_consensus for r in aggregate.raw if r.time_to_consensus >= 0]
    if reached:
        values = np.asarray(reached, dtype=np.float64)
        mean = float(values.mean())
        half = 1.96 * float(values.std(ddof=1)) / np.sqrt(values.size) if values.size > 1 else 0.0
        metrics["time_to_consensus"] = {
            "mean": mean,
            "ci95_lo": mean - half,
            "ci95_hi": mean + half,
            "n": int(values.size),
        }
    else:
        metrics["time_to_consensus"] = {"mean": None, "ci95_lo": None, "ci95_hi": None, "n": 0}
    return metrics


def _summary(result: Any, summary: dict[str, Any], spec: ModelSpec) -> dict[str, str]:
    start = float(result.diversity_series[0])
    end = float(result.diversity_series[-1])
    peak_step = int(np.argmax(result.cascade_series)) + 1 if result.cascade_series else 0
    peak = float(np.max(result.cascade_series)) if result.cascade_series else 0.0
    ttc = int(result.time_to_consensus)
    if float(summary["absorbing"]) >= 0.5:
        verdict_zh, verdict_en = "形成稳定共识", "Stable consensus"
    elif ttc >= 0:
        verdict_zh, verdict_en = "达到多数，但仍在变化", "Majority reached, still moving"
    else:
        verdict_zh, verdict_en = "尚未收敛", "Not converged"
    if ttc >= 0:
        zh = (
            f"在这组假设下，多样性从 {start:.2f} 降到 {end:.2f}；约在第 {ttc} 步达到多数。"
            f"级联峰值出现在第 {peak_step} 步，约 {peak:.0%} 的人同时改变立场。"
        )
        en = (
            f"Under these assumptions diversity fell from {start:.2f} to {end:.2f}, "
            f"reaching a majority around step {ttc}. The cascade peaked at step {peak_step}, "
            f"with about {peak:.0%} of people changing at once."
        )
    else:
        zh = (
            f"在这组假设下，多样性从 {start:.2f} 变到 {end:.2f}，但在 {spec.n_steps} 步内"
            f"没有达到多数。级联峰值在第 {peak_step} 步（{peak:.0%}）。"
        )
        en = (
            f"Under these assumptions diversity moved from {start:.2f} to {end:.2f} but no "
            f"majority formed within {spec.n_steps} steps. The cascade peaked at step "
            f"{peak_step} ({peak:.0%})."
        )
    return {"verdict_zh": verdict_zh, "verdict_en": verdict_en, "text_zh": zh, "text_en": en}


@router.post("/simulate")
async def demo_simulate(request: DemoRequest) -> dict[str, Any]:
    try:
        template = _template(request.template_key)
    except ValueError as exc:
        raise ApiError(404, "TEMPLATE_NOT_FOUND", str(exc)) from exc
    spec, graph, aggregate, result = _run(template, request)
    summary = summarize(result, spec, graph.hyperedges).to_dict()
    frame = series_frame(result)
    narrative = _summary(result, summary, spec)
    decision = build_decision_brief(
        template.key,
        template.name_zh,
        template.name_en,
        spec,
        result,
        repeats=spec.repeats,
        absorbing=float(summary["absorbing"]) >= 0.5,
    ).to_dict()
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
            "metrics": _metrics_payload(aggregate),
            "summary": summary,
            "series": {
                "steps": frame["step"].tolist(),
                "diversity": frame["diversity"].tolist(),
                "cascade": frame["cascade"].tolist(),
                "shares": result.share_series,
                "bands": _bands(aggregate),
            },
            "summary_text": narrative,
            "decision": decision,
            "opinion_count": spec.n_opinions,
            "disclaimer": DISCLAIMERS["simulation_not_prediction"],
            "disclaimer_key": "simulation_not_prediction",
        }
    }


@router.post("/narrate")
async def demo_narrate(request: DemoRequest) -> dict[str, Any]:
    """Optional local-Ollama explanation of a run; never used for metrics or decisions."""
    if not settings.ollama_enabled:
        raise ApiError(
            503,
            "OLLAMA_DISABLED",
            "Ollama narration is disabled; set OLLAMA_ENABLED=true and run ollama serve.",
        )
    try:
        template = _template(request.template_key)
    except ValueError as exc:
        raise ApiError(404, "TEMPLATE_NOT_FOUND", str(exc)) from exc
    spec, graph, aggregate, result = _run(template, request)
    summary = summarize(result, spec, graph.hyperedges).to_dict()
    narrative = _summary(result, summary, spec)
    decision = build_decision_brief(
        template.key,
        template.name_zh,
        template.name_en,
        spec,
        result,
        repeats=spec.repeats,
        absorbing=float(summary["absorbing"]) >= 0.5,
    ).to_dict()
    zh = request.lang == "zh"
    context = {
        "template": template.name_zh if zh else template.name_en,
        "question": template.question_zh if zh else template.question_en,
        "assumptions": template.assumptions_zh if zh else template.assumptions_en,
        "limitations": template.limitations_zh if zh else template.limitations_en,
        "parameters": {
            "q": spec.q,
            "latency_mu": spec.latency.mu,
            "steps": spec.n_steps,
            "replicas": spec.repeats,
            "seed": spec.seed,
        },
        "metrics": {
            name: {"mean": item.mean, "ci95": [item.ci95_lo, item.ci95_hi], "n": item.n}
            for name, item in aggregate.metrics.items()
        },
        "summary": narrative["text_zh"] if zh else narrative["text_en"],
        "timing": decision["timing"],
        "window": decision["window_zh"] if zh else decision["window_en"],
        "followups": decision["followups_zh"] if zh else decision["followups_en"],
    }
    prompt = build_prompt(context, request.lang)
    try:
        text = await generate_narration(
            prompt,
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            timeout=settings.ollama_timeout_seconds,
        )
    except OllamaError as exc:
        raise ApiError(503, "OLLAMA_UNAVAILABLE", str(exc)) from exc
    return {
        "data": {
            "text": text,
            "model": settings.ollama_model,
            "mode": "assistive-narration",
            "disclaimer_zh": "AI 辅助解释，不是结论；指标与决策以引擎输出为准。",
            "disclaimer_en": (
                "AI-assisted explanation, not a conclusion; engine outputs remain authoritative."
            ),
        }
    }


@router.post("/report", response_class=HTMLResponse)
async def demo_report(request: DemoRequest) -> HTMLResponse:
    template = _template(request.template_key)
    spec, graph, aggregate, result = _run(template, request)
    summary = summarize(result, spec, graph.hyperedges).to_dict()
    frame = series_frame(result)
    decision = build_decision_brief(
        template.key,
        template.name_zh,
        template.name_en,
        spec,
        result,
        repeats=spec.repeats,
        absorbing=float(summary["absorbing"]) >= 0.5,
    ).to_dict()
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
        decision=decision,
        narrative={
            "interpretation_zh": template.interpretation_zh,
            "interpretation_en": template.interpretation_en,
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
