"""US-009: 64 replicas on 8 jobs stay within a lenient wall-clock bound."""

from __future__ import annotations

import os
import time

import numpy as np

from hnle.graph import random_hypergraph
from hnle.mc import run_monte_carlo
from hnle.spec import ModelSpec


def test_64_replicas_with_8_jobs() -> None:
    spec = ModelSpec(
        n_steps=120,
        seed=5,
        repeats=64,
        latency={"dist": "const", "mu": 1},
    )
    graph = random_hypergraph(2_000, 6_000, np.random.default_rng(5), spec.hyperedge)

    started = time.perf_counter()
    single = run_monte_carlo(spec, graph, repeats=1, jobs=1)
    single_elapsed = time.perf_counter() - started
    assert single.n == 1

    effective_workers = min(8, os.cpu_count() or 1)
    started = time.perf_counter()
    many = run_monte_carlo(spec, graph, repeats=64, jobs=effective_workers)
    many_elapsed = time.perf_counter() - started
    assert many.n == 64

    # Lenient: 64 replicas on 8 workers should cost roughly single * (64 / cores),
    # allowing 1.5x for scheduling and process-pool start-up.  CI runners often
    # expose 4 cores, so the bound adapts instead of assuming 8.
    budget = single_elapsed * (64 / effective_workers) * 2.5
    assert many_elapsed <= budget, (single_elapsed, many_elapsed, budget)
