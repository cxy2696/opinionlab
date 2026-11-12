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

PROMPT_JA = """あなたは OpinionLab の補助解説者です。以下の JSON の数値だけを使い、
日本語で3段落の短い説明を書いてください：
1) 結果の意味：多様性、カスケードピーク、合意到達ステップ、吸収率を平易に説明する；
2) この推演が支持できる判断と、支持できない判断；
3) 次に行う実験を2つ（どのパラメータや時点を変えるか、期待される方向）。新しい数値を作らない。

厳守：JSON の数値だけを使う；実在の個人や出来事を予測しない；選挙や標的型説得の助言をしない；
単一ノードの情報を出さない；根拠が弱い場合は「不確実」と明記する。300字以内。

シミュレーション JSON：
{payload}
"""

PROMPT_DE = """Du erklärst eine OpinionLab-Simulation. Nutze ausschließlich die Zahlen
im folgenden JSON und schreibe drei kurze Absätze auf Deutsch:
1) Was die Zahlen bedeuten: Diversität, Kaskadenpeak, Konsensschritt und
   Absorptionsrate in einfacher Sprache;
2) Welche Entscheidung diese Auswertung stützen kann und welche nicht;
3) Zwei konkrete nächste Experimente (welcher Parameter oder Zeitpunkt geändert
   wird und welche Richtung erwartet wird), ohne neue Zahlen zu erfinden.

Harte Regeln: nur die gelieferten Zahlen verwenden; keine realen Personen oder
Ereignisse vorhersagen; keine Wahl- oder gezielte Überzeugungsberatung; keine
Informationen zu einzelnen Knoten ausgeben; bei schwacher Evidenz „unsicher“
sagen. Höchstens 180 Wörter.

Simulations-JSON:
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
    templates = {"en": PROMPT_EN, "ja": PROMPT_JA, "de": PROMPT_DE}
    template = templates.get(lang, PROMPT_ZH)
    guard = {
        "ja": (
            "あなたは集団意見シミュレーションの補助解説者です。"
            "提供された数値だけを使い、実在の個人や出来事を予測せず、"
            "選挙・標的型説得の助言をせず、単一ノードの情報を出さないでください。"
            "これはシミュレーションであり、結論ではないことを明示してください。"
        ),
        "de": (
            "Du bist Erklärassistent für eine Gruppenmeinungs-Simulation. "
            "Verwende nur die gelieferten Zahlen, sage keine realen Personen oder "
            "Ereignisse voraus, gib keine Wahl- oder gezielte Überzeugungsberatung, "
            "gib keine Informationen zu einzelnen Knoten aus und mache klar, dass "
            "dies eine Simulation und keine Schlussfolgerung ist."
        ),
    }.get(lang, SYSTEM_GUARD)
    return guard + "\n\n" + template.format(payload=payload)


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
