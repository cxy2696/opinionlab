"""Optional Ollama narration: off by default, guardrailed, assistive only."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest
from app import demo as demo_module
from app.main import app
from app.ollama import build_prompt, clean_narration
from app.ratelimit import reset as reset_rate_limit
from app.settings import settings

BODY = {
    "template_key": "S2",
    "q": 1.6,
    "latency_mu": 3,
    "repeats": 2,
    "seed": 7,
    "steps": 20,
    "lang": "zh",
}


def _request(path: str, **kwargs: Any) -> httpx.Response:
    async def run() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://demo"
        ) as client:
            reset_rate_limit()
            return await client.post(path, **kwargs)

    return asyncio.run(run())


def test_narration_is_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ollama_enabled", False)
    response = _request("/api/v1/demo/narrate", json=BODY)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "OLLAMA_DISABLED"


def test_narration_returns_assistive_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ollama_enabled", True)
    monkeypatch.setattr(settings, "ollama_model", "test-model")

    async def fake(*args: Any, **kwargs: Any) -> str:
        return "多样性下降说明群体在收拢；这只是模拟。"

    monkeypatch.setattr(demo_module, "generate_narration", fake)
    response = _request("/api/v1/demo/narrate", json=BODY)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["model"] == "test-model"
    assert data["mode"] == "assistive-narration"
    assert "AI 辅助解释" in data["disclaimer_zh"]
    assert "模拟" in data["text"]


def test_prompt_contains_numbers_and_guardrails() -> None:
    context = {"metrics": {"diversity_final": {"mean": 0.12}}, "summary": "测试"}
    zh = build_prompt(context, "zh")
    en = build_prompt(context, "en")
    ja = build_prompt(context, "ja")
    de = build_prompt(context, "de")
    assert "只使用" in zh and "0.12" in zh and "不要" in zh
    assert "ONLY" in en and "0.12" in en and "uncertain" in en
    assert "不確実" in ja and "0.12" in ja and "単一ノード" in ja
    assert "unsicher" in de and "0.12" in de and "einzelnen Knoten" in de


def test_narration_has_japanese_and_german_disclaimers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ollama_enabled", True)

    async def fake(*args: Any, **kwargs: Any) -> str:
        return "補助説明"

    monkeypatch.setattr(demo_module, "generate_narration", fake)
    for lang, marker in (("ja", "AIによる補助説明"), ("de", "KI-gestützte Erklärung")):
        response = _request("/api/v1/demo/narrate", json={**BODY, "lang": lang})
        assert response.status_code == 200
        data = response.json()["data"]
        assert marker in data[f"disclaimer_{lang}"]


def test_reasoning_traces_are_removed() -> None:
    assert clean_narration("<think>secret</think>\n\n可见结论") == "可见结论"
