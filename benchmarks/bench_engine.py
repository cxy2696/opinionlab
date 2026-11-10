"""Performance benchmarks (PRD G3 / OPT-20).

Run with ``make bench``. The 100k-node tier asserts the PRD budget (<= 90 s for
500 steps); CI fails the job at 120 s.
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np
import numpy.typing as npt
import pytest

from hnle.core.event import run_event
from hnle.core.sparse import run_sparse
from hnle.graph import random_hypergraph
from hnle.spec import HyperedgeSpec, ModelSpec


def _case(n_nodes: int, n_edges: int) -> tuple[ModelSpec, Any]:
    spec = ModelSpec(
        n_steps=500,
        seed=7,
        latency={"dist": "const", "mu": 1},
        hyperedge=HyperedgeSpec(min_size=2, max_size=5),
    )
    graph = random_hypergraph(n_nodes, n_edges, np.random.default_rng(7), spec.hyperedge)
    return spec, graph


def test_bench_10k_nodes(benchmark: Any) -> None:
    spec, graph = _case(10_000, 30_000)
    benchmark.pedantic(run_sparse, args=(spec, graph, 7), rounds=1, iterations=1)


@pytest.mark.slow
def test_bench_100k_nodes_under_90s() -> None:
    spec, graph = _case(100_000, 300_000)
    started = time.perf_counter()
    result = run_sparse(spec, graph, seed=7)
    elapsed = time.perf_counter() - started
    assert result.steps == 500
    assert elapsed <= 90.0, f"100k-node run took {elapsed:.1f}s (budget 90s)"


def _naive_upstream_run(
    graph: Any, seed: int, steps: int, q: float
) -> npt.NDArray[np.int64]:
    """Replica of the upstream O(sum |e|^2) nested-loop update (binary, uniform)."""
    rng = np.random.default_rng(seed)
    n_nodes = graph.n_nodes
    opinions = rng.integers(0, 2, n_nodes)
    for _ in range(steps):
        new_opinions = opinions.copy()
        for edge in graph.hyperedges:
            for node in edge:
                s1 = 0.0
                s0 = 0.0
                for other in edge:
                    if opinions[other] == 1:
                        s1 += 1.0
                    else:
                        s0 += 1.0
                p1 = s1**q / (s1**q + s0**q)
                new_opinions[node] = 1 if rng.random() < p1 else 0
        opinions = new_opinions
    return np.asarray(opinions, dtype=np.int64)


def test_csr_at_least_50x_faster_than_upstream_naive() -> None:
    spec = ModelSpec(
        n_steps=20,
        q=1.5,
        hyperedge=HyperedgeSpec(min_size=2, max_size=20),
    )
    graph = random_hypergraph(5_000, 15_000, np.random.default_rng(9), spec.hyperedge)

    started = time.perf_counter()
    _naive_upstream_run(graph, seed=3, steps=spec.n_steps, q=spec.q)
    naive_elapsed = time.perf_counter() - started

    started = time.perf_counter()
    run_sparse(spec, graph, seed=3)
    csr_elapsed = time.perf_counter() - started

    speedup = naive_elapsed / csr_elapsed
    assert speedup >= 50.0, f"CSR speedup {speedup:.1f}x is below the 50x budget"


def test_event_engine_3x_faster_at_long_latency() -> None:
    """mu=50, sigma=20, n_steps=2000: the event heap skips most frozen nodes."""
    spec = ModelSpec(
        n_steps=2_000,
        seed=5,
        q=1.5,
        latency={"dist": "normal", "mu": 50, "sigma": 20},
        hyperedge=HyperedgeSpec(min_size=2, max_size=5),
    )
    graph = random_hypergraph(20_000, 60_000, np.random.default_rng(5), spec.hyperedge)

    started = time.perf_counter()
    run_sparse(spec, graph, seed=5)
    sparse_elapsed = time.perf_counter() - started

    started = time.perf_counter()
    run_event(spec, graph, seed=5)
    event_elapsed = time.perf_counter() - started

    speedup = sparse_elapsed / event_elapsed
    assert speedup >= 3.0, f"event engine speedup {speedup:.2f}x is below 3x"
