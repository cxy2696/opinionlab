"""classical voter-model limit (q=1, L=1, pairs, uniform weights)."""

from __future__ import annotations

import numpy as np
import numpy.testing as npt

from hnle.core.sparse import run_sparse
from hnle.graph import random_hypergraph
from hnle.mc import replica_seeds
from hnle.metrics import summarize
from hnle.spec import HyperedgeSpec, ModelSpec


def _spec() -> ModelSpec:
    return ModelSpec(
        n_steps=100,
        seed=11,
        q=1.0,
        latency={"dist": "const", "mu": 1},
        hyperedge=HyperedgeSpec(min_size=2, max_size=2),
        consensus_threshold=0.8,
    )


def _consensus_rate(n_nodes: int, seeds: int = 40) -> float:
    spec = _spec()
    graph = random_hypergraph(n_nodes, 2 * n_nodes, np.random.default_rng(11), spec.hyperedge)
    replicas = replica_seeds(spec, seeds)
    hits = sum(
        1 for seed in replicas if run_sparse(spec, graph, seed).time_to_consensus >= 0
    )
    return hits / seeds


def test_consensus_probability_decays_with_population_size() -> None:
    rates = [_consensus_rate(n) for n in (100, 200, 400)]
    assert rates[0] >= rates[1] >= rates[2], rates
    assert rates[0] > rates[2], rates


def test_fixed_seed_snapshot() -> None:
    spec = _spec().model_copy(update={"seed": 7})
    graph = random_hypergraph(200, 400, np.random.default_rng(7), spec.hyperedge)
    result = run_sparse(spec, graph, seed=7)
    # Frozen snapshot: changing the update semantics or RNG streams must be
    # explained and regenerated on purpose.
    npt.assert_allclose(result.diversity_series[-1], 0.16, atol=1e-12)
    assert result.time_to_consensus == 75

    summary = summarize(result, spec, graph.hyperedges)
    assert summary.absorbing
    assert not summary.runaway
