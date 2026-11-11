"""Optional local LLM narration through Ollama.

This is deliberately *assistive*: the engine computes every number and the decision
brief. Ollama may only restate those numbers in plain language and suggest the next
experiment; it never produces metrics, predictions or per-person output.
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

SYSTEM_GUARD = (
    "You are an explanation assistant for a group-opinion simulation. "
    "Use ONLY the numbers in the provided JSON. Do not invent numbers, do not predict "
    "real individuals or events, and do not give election or persuasion advice. "
    "Make clear that results are simulations under assumptions."
)

PROMPT_ZH = """你是 OpinionLab 的辅助解读员。根据下面的模拟结果，用中文写 3 段简短说明：
1) 结果解释：把多样性、级联峰值、收敛步和吸收比例翻译成人话；
2) 这意味着什么：这项推演能支持什么判断，不能支持什么；
3) 下一步推演：给出 2 个具体建议（改哪个参数/时点、预期方向），不要编造新数字。

严格约束：只使用 JSON 中的数字；不要预测真实个人或事件；不要做选举或定向说服建议；
不要输出任何单节点信息；如果证据不足要明确说“不确定”。控制在 220 字以内。

模拟结果 JSON：
{payload}
"""

PROMPT_EN = """You explain an OpinionLab simulation. Using ONLY the JSON below,
write 3 short paragraphs:
1) What the numbers mean: diversity, cascade peak, consensus step and absorbing rate,
   in plain language;
2) What decision this can and cannot support;
3) Two concrete next experiments (which parameter/timing to change and the expected direction),
   without inventing new numbers.

Hard rules: use only the provided numbers; do not predict real individuals or events; no election or
targeted-persuasion advice; no per-node output; say "uncertain" when evidence is weak. Keep under
180 words.

Simulation JSON:
{payload}
"""


THINK_BLOCK = re.compile(r"<think\b[^>]*>.*?</think>", re.IGNORECASE | re.DOTALL)


def clean_narration(text: str) -> str:
    """Drop reasoning traces some local models (e.g. DeepSeek-R1) emit."""
    cleaned = THINK_BLOCK.sub("", text).strip()
    return cleaned[:2000]


class OllamaError(RuntimeError):
    """Raised when the local Ollama service is unavailable or returns invalid data."""


def build_prompt(context: dict[str, Any], lang: str = "zh") -> str:
    payload = json.dumps(context, ensure_ascii=False, indent=2, sort_keys=True)
    template = PROMPT_EN if lang == "en" else PROMPT_ZH
    return SYSTEM_GUARD + "\n\n" + template.format(payload=payload)


async def generate_narration(
    prompt: str,
    *,
    base_url: str,
    model: str,
    timeout: float = 45.0,
) -> str:
    url = base_url.rstrip("/") + "/api/generate"
    body = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 320},
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=body)
    except httpx.HTTPError as exc:
        raise OllamaError(f"Ollama is not reachable at {base_url}") from exc
    if response.status_code != 200:
        raise OllamaError(f"Ollama returned HTTP {response.status_code}")
    try:
        data = response.json()
    except ValueError as exc:
        raise OllamaError("Ollama returned invalid JSON") from exc
    text = clean_narration(str(data.get("response", "")))
    if not text:
        raise OllamaError("Ollama returned an empty response")
    return text
