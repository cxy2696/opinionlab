"""freeze five representative V1 benchmark configurations.

Regenerate only with ``UPDATE_GOLDEN=1`` and explain the numeric change in the
commit message.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import numpy as np

from hnle.engine import run_engine
from hnle.graph import Hypergraph, random_hypergraph
from hnle.metrics import summarize
from hnle.spec import Engine, ModelSpec

GOLDEN = Path(__file__).parent / "golden" / "v1_baseline.json"
METRIC_KEYS = (
    "diversity_final",
    "entropy_final",
    "time_to_consensus",
    "cascade_p99",
    "absorbing",
)


def _cases() -> list[tuple[str, ModelSpec, Hypergraph]]:
    binary = ModelSpec(n_steps=80, seed=7, q=1.5, latency={"dist": "const", "mu": 1})
    binary_graph = random_hypergraph(60, 120, np.random.default_rng(7), binary.hyperedge)

    multi = ModelSpec(
        n_steps=60,
        seed=11,
        q=1.2,
        n_opinions=3,
        decision_rule="argmax",
        latency={"dist": "exponential", "mu": 2},
    )
    multi_graph = random_hypergraph(50, 100, np.random.default_rng(11), multi.hyperedge)

    evolving = ModelSpec(
        n_steps=50,
        seed=5,
        q=1.8,
        topology={"mode": "time_varying", "arrival_rate": 0.5, "decay_rate": 0.02},
        shocks=[{"at_step": 10, "type": "flip_share", "magnitude": 0.2, "duration": 1}],
        latency={"dist": "normal", "mu": 3, "sigma": 1},
    )
    evolving_graph = random_hypergraph(60, 120, np.random.default_rng(5), evolving.hyperedge)

    event = ModelSpec(
        n_steps=40,
        seed=3,
        q=1.5,
        engine=Engine.event_driven,
        latency={"dist": "const", "mu": 1},
    )
    event_graph = random_hypergraph(40, 80, np.random.default_rng(3), event.hyperedge)

    voter = ModelSpec(
        n_steps=100,
        seed=9,
        q=1.0,
        latency={"dist": "const", "mu": 1},
        hyperedge={"min_size": 2, "max_size": 2},
    )
    voter_graph = random_hypergraph(80, 160, np.random.default_rng(9), voter.hyperedge)

    return [
        ("binary_mean_stochastic", binary, binary_graph),
        ("multi_opinion_argmax", multi, multi_graph),
        ("time_varying_shock", evolving, evolving_graph),
        ("event_unit_latency", event, event_graph),
        ("voter_limit_q1", voter, voter_graph),
    ]


def _compute() -> dict[str, dict[str, float]]:
    baseline: dict[str, dict[str, float]] = {}
    for name, spec, graph in _cases():
        result = run_engine(spec, graph, spec.seed)
        summary = summarize(result, spec, graph.hyperedges).to_dict()
        baseline[name] = {
            key: float(summary[key])  # type: ignore[arg-type]
            for key in METRIC_KEYS
        }
        baseline[name]["cascade_mean"] = float(np.mean(result.cascade_series))
    return baseline


def test_five_frozen_configurations() -> None:
    computed = _compute()
    if os.environ.get("UPDATE_GOLDEN") == "1":
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(json.dumps(computed, indent=2, sort_keys=True) + "\n")
        return
    expected: dict[str, Any] = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert len(expected) == 5
    for name, metrics in expected.items():
        assert name in computed, name
        for key, value in metrics.items():
            np.testing.assert_allclose(
                computed[name][key], value, atol=1e-12, err_msg=f"{name}/{key}"
            )


def test_golden_is_deterministic() -> None:
    assert _compute() == _compute()
