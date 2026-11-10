"""G1 / OPT-12: identical seeds yield identical results regardless of jobs."""

from __future__ import annotations

import numpy as np

from hnle.graph import random_hypergraph
from hnle.mc import run_monte_carlo
from hnle.spec import ModelSpec


def _spec() -> ModelSpec:
    return ModelSpec(
        n_steps=40,
        seed=21,
        q=1.5,
        repeats=4,
        latency={"dist": "normal", "mu": 2, "sigma": 1},
    )


def test_jobs_do_not_change_results() -> None:
    spec = _spec()
    graph = random_hypergraph(40, 80, np.random.default_rng(21), spec.hyperedge)
    serial = run_monte_carlo(spec, graph, repeats=4, jobs=1, collect_raw=True)
    parallel = run_monte_carlo(spec, graph, repeats=4, jobs=8, collect_raw=True)
    assert serial.raw is not None and parallel.raw is not None
    assert len(serial.raw) == len(parallel.raw) == 4
    for one, many in zip(serial.raw, parallel.raw, strict=True):
        np.testing.assert_array_equal(one.opinions, many.opinions)
        np.testing.assert_allclose(one.diversity_series, many.diversity_series, atol=1e-12)
        assert one.time_to_consensus == many.time_to_consensus
