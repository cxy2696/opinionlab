"""Turn simulation output into a decision brief: what it can inform, when to act, what next.

The brief is deliberately conservative: it frames timing as a *simulated window*
under stated assumptions, never as a prediction of when a real event will happen.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from hnle.core.update import RunResult
from hnle.spec import ModelSpec

DECISIONS: dict[str, tuple[str, str]] = {
    "S1": ("政策分阶段发布的节奏与窗口", "cadence and windows for staged policy releases"),
    "S2": ("辟谣/更正信息的投放时点与力度", "timing and strength of debunking or corrections"),
    "S3": ("平台治理动作的介入时机", "when to intervene with platform governance"),
    "S4": ("品牌 KOL 与普通用户的配比节奏", "the mix and cadence of KOL vs organic reach"),
    "S5": ("应急科普的投放时点", "when to push emergency science communication"),
    "S6": ("金融预期沟通的节奏", "cadence of financial-expectation communication"),
    "S7": (
        "社区议事是否需要轻推、何时轻推",
        "whether and when to facilitate a community discussion",
    ),
    "S8": (
        "组织变革沟通的节奏与窗口",
        "cadence and windows for organizational-change communication",
    ),
    "S9": ("新品发布的投放节奏", "launch cadence for a new product"),
    "G1": (
        "模型行为是否符合经典极限（研究判断）",
        "whether model behaviour matches the classical limit",
    ),
    "G2": ("事实核查的介入时点", "when fact-checking should step in"),
    "G3": ("公共卫生信息的集中投放时点", "when to concentrate public-health messaging"),
    "G4": ("平台系统性风险的观察窗口", "observation windows for platform systemic risk"),
    "G5": (
        "选举类研究的合规边界（需审批）",
        "compliance boundaries for election research (approval required)",
    ),
    "G6": ("灾害预警的发布时点", "when to issue a disaster warning"),
    "G7": ("企业变更沟通的节奏", "cadence of corporate-change communication"),
}
GENERIC_DECISION = ("沟通/干预的时点与力度", "when and how strongly to communicate or intervene")


@dataclass
class DecisionBrief:
    decision_zh: str
    decision_en: str
    takeoff_step: int | None
    peak_step: int | None
    consensus_step: int | None
    intervention_step: int | None
    window_zh: str
    window_en: str
    followups_zh: list[str]
    followups_en: list[str]
    caveat_zh: str
    caveat_en: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_zh": self.decision_zh,
            "decision_en": self.decision_en,
            "timing": {
                "takeoff_step": self.takeoff_step,
                "peak_step": self.peak_step,
                "consensus_step": self.consensus_step,
                "intervention_step": self.intervention_step,
            },
            "window_zh": self.window_zh,
            "window_en": self.window_en,
            "followups_zh": self.followups_zh,
            "followups_en": self.followups_en,
            "caveat_zh": self.caveat_zh,
            "caveat_en": self.caveat_en,
        }


def build_decision_brief(
    template_key: str,
    name_zh: str,
    name_en: str,
    spec: ModelSpec,
    result: RunResult,
    *,
    repeats: int = 1,
    absorbing: bool = False,
) -> DecisionBrief:
    decision_zh, decision_en = DECISIONS.get(template_key, GENERIC_DECISION)
    cascade = np.asarray(result.cascade_series, dtype=np.float64)
    if cascade.size:
        threshold = max(0.02, float(cascade.mean()) * 2.0)
        hits = np.nonzero(cascade >= threshold)[0]
        takeoff = int(hits[0]) + 1 if hits.size else None
        peak = int(np.argmax(cascade)) + 1
        peak_value = float(cascade.max())
    else:  # pragma: no cover - engines always produce a series
        takeoff, peak, peak_value = None, None, 0.0
    consensus = result.time_to_consensus if result.time_to_consensus >= 0 else None
    intervention = spec.interventions[0].at_step if spec.interventions else None

    lead = max(2, int(round(2 * spec.latency.mu)))
    if peak is not None and intervention is not None:
        start = max(1, peak - lead)
        window_zh = (
            f"建议把干预放在第 {start}–{peak} 步：峰值前约 {lead} 步（约两个反应周期）。"
            f"本次配置在第 {intervention} 步。"
        )
        window_en = (
            f"A simulated window is steps {start}–{peak}: about {lead} steps before the "
            f"cascade peak (roughly two reaction cycles). This run intervenes at step "
            f"{intervention}."
        )
    elif peak is not None:
        start = takeoff or max(1, peak - lead)
        window_zh = (
            f"重点观察第 {start}–{peak} 步：级联约在第 {start} 步起势，"
            f"第 {peak} 步达到峰值（{peak_value:.0%} 的人同时改变立场）。"
        )
        window_en = (
            f"Watch steps {start}–{peak}: the cascade takes off around step {start} and "
            f"peaks at step {peak} ({peak_value:.0%} of people changing at once)."
        )
    else:  # pragma: no cover
        window_zh = "没有观察到明显级联，可优先检查参数与拓扑。"
        window_en = "No clear cascade was observed; check parameters and topology first."

    if consensus is not None:
        window_zh += f"约第 {consensus} 步达到多数。"
        window_en += f" A majority is reached around step {consensus}."

    followups_zh = [
        "把本次参数当作基线，只改一个时点重跑；只有两次的 95% CI 不重叠，才谈“时点有效”。",
        "把副本数加到 30 以上再确认结论；当前副本数为 "
        f"{repeats}，区间可能偏宽。",
        "用真实数据校准 q、时延与初始态度分布；这里的时点是模拟窗口，不是事件预测。",
    ]
    followups_en = [
        "Treat this run as the baseline, change only the timing, and rerun; call the timing "
        "effective only when the two 95% CIs do not overlap.",
        f"Raise replicas to 30+ before relying on the result (currently {repeats}); the "
        "interval may be wide.",
        "Calibrate q, latency and initial stances on real data; the window here is simulated, "
        "not an event forecast.",
    ]
    if absorbing and consensus is not None:
        followups_zh.append("如果目标是推迟共识，尝试增大时延或降低 q，看窗口是否随之后移。")
        followups_en.append(
            "If the goal is to delay consensus, try longer latency or lower q and see whether "
            "the window moves later."
        )

    return DecisionBrief(
        decision_zh=decision_zh,
        decision_en=decision_en,
        takeoff_step=takeoff,
        peak_step=peak,
        consensus_step=consensus,
        intervention_step=intervention,
        window_zh=window_zh,
        window_en=window_en,
        followups_zh=followups_zh[:3],
        followups_en=followups_en[:3],
        caveat_zh="时点建议来自给定假设下的模拟，不构成对真实事件时间的预测。",
        caveat_en="Timing advice comes from a simulation under stated assumptions and is not "
        "a forecast of real event timing.",
    )
