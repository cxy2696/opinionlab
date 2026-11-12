"""Welford confidence intervals and sample-size guardrails."""

from __future__ import annotations

import numpy as np
import pytest

from hnle.graph import Hypergraph, random_hypergraph
from hnle.mc import run_monte_carlo
from hnle.spec import ModelSpec


def _case(repeats: int) -> tuple[ModelSpec, Hypergraph]:
    spec = ModelSpec(n_steps=20, seed=3, repeats=repeats, latency={"dist": "const", "mu": 1})
    graph = random_hypergraph(40, 80, np.random.default_rng(3), spec.hyperedge)
    return spec, graph


def test_metric_subset_limits_the_aggregate_keys() -> None:
    spec = ModelSpec(
        n_steps=5,
        seed=3,
        repeats=2,
        latency={"dist": "const", "mu": 1},
        metrics=["diversity_final"],
    )
    graph = random_hypergraph(20, 40, np.random.default_rng(3), spec.hyperedge)
    result = run_monte_carlo(spec, graph, repeats=2)
    assert set(result.metrics) == {"diversity_final"}


def test_every_metric_has_mean_and_interval() -> None:
    spec, graph = _case(30)
    result = run_monte_carlo(spec, graph, repeats=30)
    assert result.n == 30
    assert not result.insufficient_samples
    assert result.metrics["diversity_final"].n == 30
    ci = result.metrics["diversity_final"]
    assert ci.ci95_lo <= ci.mean <= ci.ci95_hi
    assert "cascade_p99" in result.metrics
    assert result.to_dict()["metrics"]["diversity_final"]["n"] == 30


def test_small_sample_warns_and_marks_insufficient() -> None:
    spec, graph = _case(5)
    with pytest.warns(RuntimeWarning, match="underpowered"):
        result = run_monte_carlo(spec, graph, repeats=5)
    assert result.insufficient_samples
    assert result.metrics["diversity_final"].n == 5


def test_raw_curves_only_when_requested() -> None:
    spec, graph = _case(4)
    result = run_monte_carlo(spec, graph, repeats=4)
    assert result.raw is None
    with_raw = run_monte_carlo(spec, graph, repeats=4, collect_raw=True)
    assert with_raw.raw is not None
    assert len(with_raw.raw) == 4


def test_memory_guardrail_degrades_to_streaming() -> None:
    spec, graph = _case(8)
    with pytest.warns(RuntimeWarning, match="max_memory_gb"):
        result = run_monte_carlo(spec, graph, repeats=8, collect_raw=True, max_memory_gb=1e-9)
    assert result.degraded_to_streaming
    assert result.raw is None
    assert result.metrics["diversity_final"].n == 8
