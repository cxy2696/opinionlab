"""US-005: the three decision rules and the RNG contract."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from hnle.core.sparse import run_sparse
from hnle.graph import Hypergraph
from hnle.spec import DecisionRule, ModelSpec

CORE_DIR = Path(__file__).parents[1] / "packages" / "hnle" / "src" / "hnle" / "core"


def _graph() -> Hypergraph:
    return Hypergraph(n_nodes=30, hyperedges=tuple((i, i + 1, i + 2) for i in range(28)))


def test_threshold_rule_uses_spec_threshold() -> None:
    low = ModelSpec(
        n_steps=1,
        decision_rule=DecisionRule.threshold,
        threshold=0.01,
        latency={"dist": "const", "mu": 1},
        init_mode="data_driven",
    )
    high = low.model_copy(update={"threshold": 0.99})
    graph = Hypergraph(
        n_nodes=10,
        hyperedges=((0, 1, 2),),
        initial_opinions=(1, 0, 0, 1, 0, 1, 0, 1, 0, 1),
    )
    low_run = run_sparse(low, graph, seed=4)
    high_run = run_sparse(high, graph, seed=4)
    # p1 on the only edge is 0.5: threshold 0.01 flips to 1, 0.99 keeps 0.
    assert low_run.opinions[0] == 1
    assert high_run.opinions[0] == 0


def test_argmax_mode_has_zero_variance_across_replicas() -> None:
    graph = Hypergraph(
        n_nodes=30,
        hyperedges=tuple((i, i + 1, i + 2) for i in range(28)),
        initial_opinions=tuple(i % 2 for i in range(30)),
    )
    spec = ModelSpec(
        n_steps=20,
        decision_rule=DecisionRule.argmax,
        init_mode="data_driven",
        latency={"dist": "const", "mu": 1},
    )
    first = run_sparse(spec, graph, seed=1)
    second = run_sparse(spec, graph, seed=2)
    third = run_sparse(spec, graph, seed=3)
    np.testing.assert_array_equal(first.opinions, second.opinions)
    np.testing.assert_array_equal(first.opinions, third.opinions)
    np.testing.assert_array_equal(first.diversity_series, second.diversity_series)
    assert np.var([first.diversity_series[-1], second.diversity_series[-1],
                   third.diversity_series[-1]]) == 0.0


def test_zero_denominator_falls_back_to_uniform_and_warns() -> None:
    graph = Hypergraph(n_nodes=4, hyperedges=((0, 1), (2, 3)))
    spec = ModelSpec(
        n_steps=3,
        latency={"dist": "const", "mu": 1},
        weights={"source": "custom", "custom": {"0": 0.0, "1": 0.0, "2": 0.0, "3": 0.0}},
    )
    result = run_sparse(spec, graph, seed=5)
    assert result.warn_counts["zero_denominator_edges"] >= 1
    assert np.isfinite(result.diversity_series).all()


def test_core_does_not_use_global_rng() -> None:
    forbidden = [
        "np.random.seed",
        "np.random.rand(",
        "np.random.randn",
        "np.random.choice",
        "np.random.randint",
        "random.random",
        "random.seed",
    ]
    for path in CORE_DIR.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in source, f"{path} uses global RNG: {token}"
