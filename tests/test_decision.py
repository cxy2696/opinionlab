"""Decision brief: what the run informs, timing nodes and follow-ups."""

from __future__ import annotations

import numpy as np

from hnle.core.sparse import run_sparse
from hnle.decision import build_decision_brief
from hnle.graph import random_hypergraph
from hnle.metrics import summarize
from hnle.spec import ModelSpec


def _brief(template_key: str = "S2", with_intervention: bool = True) -> dict[str, object]:
    payload = {
        "n_steps": 60,
        "q": 1.6,
        "seed": 3,
        "latency": {"dist": "normal", "mu": 3, "sigma": 1},
    }
    if with_intervention:
        payload["interventions"] = [
            {
                "at_step": 20,
                "type": "debunk",
                "target": {"opinion": "1"},
                "magnitude": 0.3,
                "duration": 5,
            }
        ]
    spec = ModelSpec.model_validate(payload)
    graph = random_hypergraph(120, 300, np.random.default_rng(3), spec.hyperedge)
    result = run_sparse(spec, graph, spec.seed)
    summary = summarize(result, spec, graph.hyperedges)
    brief = build_decision_brief(
        template_key,
        "辟谣时机",
        "Rumor debunk timing",
        spec,
        result,
        repeats=spec.repeats,
        absorbing=summary.absorbing,
    )
    return brief.to_dict()


def test_decision_brief_contains_timing_and_followups() -> None:
    brief = _brief()
    assert "辟谣" in str(brief["decision_zh"])
    timing = brief["timing"]
    assert isinstance(timing, dict)
    assert timing["peak_step"] is not None
    assert timing["intervention_step"] == 20
    assert "第" in str(brief["window_zh"])
    assert 0 < len(brief["followups_zh"]) <= 4
    assert any("CI" in item for item in brief["followups_zh"])
    assert "预测" in str(brief["caveat_zh"])


def test_window_without_intervention_uses_cascade_peak() -> None:
    brief = _brief(with_intervention=False)
    assert "观察" in str(brief["window_zh"])
    assert brief["timing"]["intervention_step"] is None


def test_unknown_template_falls_back_to_generic_decision() -> None:
    brief = _brief(template_key="ZZ")
    assert "沟通" in str(brief["decision_zh"]) or "干预" in str(brief["decision_zh"])


def test_absorbing_run_keeps_the_fourth_followup() -> None:
    from hnle.decision import build_decision_brief
    from hnle.spec import ModelSpec

    class _Result:
        cascade_series = [0.0, 0.1, 0.25, 0.05]
        time_to_consensus = 3

    spec = ModelSpec(n_steps=4, latency={"dist": "const", "mu": 1})
    brief = build_decision_brief(
        "S2", "辟谣时机", "Rumor debunk timing", spec, _Result(), repeats=8, absorbing=True
    )
    assert len(brief.followups_zh) == 4
    assert any("推迟" in item for item in brief.followups_zh)
