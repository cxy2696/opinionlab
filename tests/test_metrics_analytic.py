"""US-008: analytic checks for the rebuilt metric set."""

from __future__ import annotations

import numpy as np

from hnle.core.sparse import run_sparse
from hnle.graph import Hypergraph
from hnle.metrics import (
    cascade_quantiles,
    consensus_stability,
    diversity,
    foster_polarization,
    is_oscillating,
    n_active_opinions,
    opinion_shares,
    shannon_entropy,
    summarize,
    time_to_consensus,
)
from hnle.spec import ModelSpec


def test_unanimous_state_has_zero_diversity_and_entropy() -> None:
    opinions = np.zeros(10, dtype=np.int64)
    assert diversity(opinions, 2) == 0.0
    assert shannon_entropy(opinions, 2) == 0.0
    assert foster_polarization(opinions, 2) == 0.0
    assert n_active_opinions(opinions, 2) == 1


def test_uniform_binary_state() -> None:
    opinions = np.asarray([0] * 5 + [1] * 5, dtype=np.int64)
    np.testing.assert_allclose(opinion_shares(opinions, 2), [0.5, 0.5])
    assert diversity(opinions, 2) == 0.5
    assert shannon_entropy(opinions, 2) == 1.0  # log2(2)
    assert foster_polarization(opinions, 2) == 1.0
    assert n_active_opinions(opinions, 2) == 2


def test_sine_is_oscillating_and_convergence_is_not() -> None:
    t = np.arange(200, dtype=np.float64)
    sine = list(0.5 + 0.35 * np.sin(2.0 * np.pi * t / 20.0) + 0.0005 * t)
    decay = list(0.5 * np.exp(-t / 25.0))
    assert is_oscillating(sine)
    assert not is_oscillating(decay)


def test_cascade_quantiles() -> None:
    quantiles = cascade_quantiles([0.1, 0.2, 0.3, 0.4])
    assert quantiles["cascade_max"] == 0.4
    np.testing.assert_allclose(quantiles["cascade_p50"], 0.25)
    assert cascade_quantiles([])["cascade_max"] == 0.0


def test_time_to_consensus_and_stability() -> None:
    series = [0.5, 0.4, 0.2, 0.2, 0.2, 0.2]
    assert time_to_consensus(series, 0.8) == 2
    assert consensus_stability(series, 0.8, window=3)
    rebound = [0.5, 0.2, 0.2, 0.5, 0.2, 0.2]
    assert not consensus_stability(rebound, 0.8, window=3)
    assert time_to_consensus([0.9, 0.9], 0.8) == -1


def test_summarize_reports_every_field() -> None:
    spec = ModelSpec(n_steps=30, seed=4, q=1.5)
    graph = Hypergraph(
        n_nodes=20,
        hyperedges=tuple((i, i + 1) for i in range(19)),
        initial_opinions=tuple(i % 2 for i in range(20)),
    )
    result = run_sparse(spec, graph, seed=4)
    summary = summarize(result, spec, graph.hyperedges).to_dict()
    assert 0.0 <= float(summary["diversity_final"]) <= 0.5
    assert float(summary["entropy_final"]) >= 0.0
    assert int(summary["n_active_opinions"]) >= 1
    assert all(np.isfinite(value) for value in summary.values() if isinstance(value, float))
