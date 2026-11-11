"""Public demo application: page, templates, simulation and report."""

from __future__ import annotations

import asyncio

import httpx
from app.main import app
from app.ratelimit import reset as reset_rate_limit

BODY = {
    "template_key": "S2",
    "q": 1.6,
    "latency_mu": 3,
    "repeats": 4,
    "seed": 7,
    "steps": 40,
}


def _request(method: str, path: str, **kwargs: object) -> httpx.Response:
    async def run() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://demo"
        ) as client:
            reset_rate_limit()
            return await client.request(method, path, **kwargs)  # type: ignore[arg-type]

    return asyncio.run(run())


def test_root_redirects_to_demo_app() -> None:
    response = _request("GET", "/", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert response.headers["location"] == "/api/v1/demo/app"


def test_demo_page_is_self_contained() -> None:
    response = _request("GET", "/api/v1/demo/app")
    assert response.status_code == 200
    html = response.text
    assert "OpinionLab" in html
    assert "/api/v1/demo/echarts.js" in html
    assert "/api/v1/demo/static/app.js" in html
    assert "/api/v1/demo/static/style.css" in html
    assert "非对真实舆情的预测" in html
    assert "not a prediction" in html


def test_echarts_bundle_is_served_locally() -> None:
    response = _request("GET", "/api/v1/demo/echarts.js")
    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]
    assert len(response.text) > 100_000
    assert "Apache" in response.text


def test_templates_endpoint_lists_enabled_templates() -> None:
    response = _request("GET", "/api/v1/demo/templates")
    assert response.status_code == 200
    payload = response.json()
    keys = {item["key"] for item in payload["data"]}
    assert {"S2", "G1"} <= keys
    s2 = next(item for item in payload["data"] if item["key"] == "S2")
    assert s2["question_zh"] and s2["question_en"]
    assert "q" in s2["defaults"]


def test_demo_simulation_is_reproducible() -> None:
    first = _request("POST", "/api/v1/demo/simulate", json=BODY)
    second = _request("POST", "/api/v1/demo/simulate", json=BODY)
    assert first.status_code == second.status_code == 200
    left = first.json()["data"]
    right = second.json()["data"]
    assert left["series"]["diversity"] == right["series"]["diversity"]
    metrics = left["metrics"]
    for name in ("diversity_final", "cascade_p99", "time_to_consensus"):
        assert {"mean", "ci95_lo", "ci95_hi", "n"} <= set(metrics[name])
    assert len(left["series"]["steps"]) == 41  # n_steps + initial point
    assert len(left["series"]["shares"]) == 41
    assert len(left["series"]["shares"][0]) == 2
    assert len(left["series"]["bands"]["p50"]) == 41
    assert {"verdict_zh", "verdict_en", "text_zh", "text_en"} <= set(left["summary_text"])
    decision = left["decision"]
    assert {"decision_zh", "decision_en", "window_zh", "window_en"} <= set(decision)
    assert {"takeoff_step", "peak_step", "consensus_step", "intervention_step"} <= set(
        decision["timing"]
    )
    assert decision["followups_zh"]
    assert left["disclaimer_key"] == "simulation_not_prediction"


def test_unknown_template_returns_404() -> None:
    response = _request("POST", "/api/v1/demo/simulate", json={**BODY, "template_key": "NOPE"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TEMPLATE_NOT_FOUND"


def test_demo_report_contains_disclaimer_and_ci() -> None:
    response = _request("POST", "/api/v1/demo/report", json=BODY)
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    html = response.text
    assert "非对真实舆情的预测" in html
    assert "not a prediction" in html
    assert "95% CI" in html
    assert "决策提示" in html
    assert "建议后续" in html
    assert "echarts" in html.lower()


def test_demo_static_assets() -> None:
    script = _request("GET", "/api/v1/demo/static/app.js")
    style = _request("GET", "/api/v1/demo/static/style.css")
    assert script.status_code == style.status_code == 200
    assert "renderCharts" in script.text
    assert "--accent" in style.text
