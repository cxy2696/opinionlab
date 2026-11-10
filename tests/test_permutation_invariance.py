"""G2 / OPT-01: results must not depend on hyperedge list order."""

from __future__ import annotations

import numpy as np
import numpy.testing as npt

from hnle.core.sparse import run_sparse
from hnle.graph import Hypergraph, random_hypergraph
from hnle.spec import ModelSpec


def _build() -> tuple[ModelSpec, Hypergraph]:
    spec = ModelSpec(
        n_steps=60,
        seed=17,
        q=1.5,
        latency={"dist": "const", "mu": 1},
        n_opinions=2,
        aggregation="mean",
    )
    return spec, random_hypergraph(60, 120, np.random.default_rng(5), spec.hyperedge)


def test_permutation_invariance_atol_zero() -> None:
    spec, graph = _build()
    baseline = run_sparse(spec, graph, seed=spec.seed)

    for trial in range(10):
        permutation = np.random.default_rng(1000 + trial).permutation(len(graph.hyperedges))
        edges = tuple(graph.hyperedges[int(i)] for i in permutation)
        permuted = Hypergraph(n_nodes=graph.n_nodes, hyperedges=edges)
        result = run_sparse(spec, permuted, seed=spec.seed)
        npt.assert_allclose(result.diversity_series, baseline.diversity_series, atol=0.0)
        npt.assert_allclose(result.cascade_series, baseline.cascade_series, atol=0.0)
        np.testing.assert_array_equal(result.opinions, baseline.opinions)
        assert result.time_to_consensus == baseline.time_to_consensus
