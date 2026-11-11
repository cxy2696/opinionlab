"""Check the shared binary fixture against this repository's kernel."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from hnle.core.update import aggregate_node_probabilities, edge_distributions, node_weights
from hnle.graph import Hypergraph
from hnle.spec import Aggregation, ModelSpec

FIXTURE = Path(__file__).parents[1] / "conformance" / "binary_case.json"
CASES = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]


@pytest.mark.parametrize("case", CASES, ids=[case["name"] for case in CASES])
def test_shared_binary_fixture(case: dict) -> None:
    graph = Hypergraph(
        n_nodes=case["n_nodes"],
        hyperedges=tuple(tuple(edge) for edge in case["edges"]),
        weights=tuple(case["weights"]),
    )
    spec = ModelSpec(
        q=case["q"],
        n_opinions=2,
        weights={
            "source": "custom",
            "custom": {str(i): float(w) for i, w in enumerate(case["weights"])},
            "normalize": "none",
        },
    )
    weights, warnings = node_weights(spec, graph)
    assert warnings == {}
    np.testing.assert_allclose(weights, case["weights"], atol=1e-12)

    opinions = np.asarray(case["opinions"], dtype=np.int64)
    edge_probs, zero_edges = edge_distributions(spec, graph.hyperedges, opinions, weights)
    assert zero_edges == 0
    np.testing.assert_allclose(edge_probs[:, 1], case["expected_edge_p1"], atol=1e-12)

    incident: list[list[int]] = [[] for _ in range(case["n_nodes"])]
    for edge_idx, edge in enumerate(graph.hyperedges):
        for node in edge:
            incident[node].append(edge_idx)
    sizes = np.asarray([len(edge) for edge in graph.hyperedges], dtype=np.float64)
    node_probs = aggregate_node_probabilities(edge_probs, sizes, incident, Aggregation.mean)
    np.testing.assert_allclose(node_probs[:, 1], case["expected_node_p1"], atol=1e-12)
