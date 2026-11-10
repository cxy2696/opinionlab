"""the CSR kernel matches the readable node-centric reference."""

from __future__ import annotations

import numpy as np
import numpy.testing as npt

from hnle.core.sparse import run_sparse
from hnle.core.update import run_simulation
from hnle.graph import Hypergraph, random_hypergraph
from hnle.spec import Aggregation, ModelSpec


def _case(aggregation: Aggregation) -> tuple[ModelSpec, Hypergraph]:
    spec = ModelSpec(
        n_steps=40,
        seed=13,
        q=1.5,
        n_opinions=3,
        aggregation=aggregation,
        latency={"dist": "exponential", "mu": 2},
        init_mode="fixed_ratio",
        target_share_1=0.4,
    )
    graph = random_hypergraph(40, 70, np.random.default_rng(13), spec.hyperedge)
    return spec, graph


def test_csr_matches_reference_for_every_aggregation() -> None:
    for aggregation in (Aggregation.mean, Aggregation.max, Aggregation.size_weighted):
        spec, graph = _case(aggregation)
        reference = run_simulation(spec, graph, seed=spec.seed)
        fast = run_sparse(spec, graph, seed=spec.seed)
        npt.assert_allclose(fast.diversity_series, reference.diversity_series, atol=1e-12)
        npt.assert_allclose(fast.cascade_series, reference.cascade_series, atol=1e-12)
        np.testing.assert_array_equal(fast.opinions, reference.opinions)
        assert fast.time_to_consensus == reference.time_to_consensus


def test_csr_handles_multi_opinion_and_weights() -> None:
    spec, graph = _case(Aggregation.mean)
    graph = Hypergraph(
        n_nodes=graph.n_nodes,
        hyperedges=graph.hyperedges,
        initial_opinions=tuple(i % 3 for i in range(graph.n_nodes)),
    )
    payload = spec.model_dump()
    payload["weights"] = {
        "source": "custom",
        "custom": {str(i): (i % 5) + 1 for i in range(40)},
    }
    weighted = ModelSpec.model_validate(payload)
    reference = run_simulation(weighted, graph, seed=5)
    fast = run_sparse(weighted, graph, seed=5)
    npt.assert_allclose(fast.diversity_series, reference.diversity_series, atol=1e-12)
    np.testing.assert_array_equal(fast.opinions, reference.opinions)


def test_csr_is_permutation_invariant() -> None:
    spec, graph = _case(Aggregation.mean)
    baseline = run_sparse(spec, graph, seed=spec.seed)
    permutation = np.random.default_rng(7).permutation(len(graph.hyperedges))
    permuted = Hypergraph(
        n_nodes=graph.n_nodes,
        hyperedges=tuple(graph.hyperedges[int(i)] for i in permutation),
    )
    result = run_sparse(spec, permuted, seed=spec.seed)
    npt.assert_allclose(result.diversity_series, baseline.diversity_series, atol=0.0)
    np.testing.assert_array_equal(result.opinions, baseline.opinions)


def test_source_has_no_iterrows() -> None:
    from pathlib import Path

    root = Path(__file__).parents[1] / "packages" / "hnle" / "src" / "hnle"
    for path in root.rglob("*.py"):
        assert ".iterrows(" not in path.read_text(encoding="utf-8"), path
