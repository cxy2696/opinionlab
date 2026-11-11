"""weight sources are actually consumed by the engine."""

from __future__ import annotations

import numpy as np

from hnle.core.update import edge_distributions, node_weights
from hnle.graph import Hypergraph
from hnle.io.manifest import load_graph, save_graph
from hnle.spec import ModelSpec


def test_engagement_weights_come_from_the_graph() -> None:
    graph = Hypergraph(2, ((0, 1),), weights=(1.0, 3.0))
    spec = ModelSpec(q=1.0, weights={"source": "engagement", "normalize": "max"})
    weights, warnings = node_weights(spec, graph)
    np.testing.assert_allclose(weights, [1.0 / 3.0, 1.0])
    assert warnings == {}

    probs, _ = edge_distributions(spec, graph.hyperedges, np.array([0, 1]), weights)
    np.testing.assert_allclose(probs[0, 1], 0.75)


def test_engagement_without_graph_weights_falls_back_to_uniform() -> None:
    graph = Hypergraph(2, ((0, 1),))
    spec = ModelSpec(q=1.0, weights={"source": "engagement", "normalize": "max"})
    weights, warnings = node_weights(spec, graph)
    np.testing.assert_allclose(weights, [1.0, 1.0])
    assert warnings["missing_engagement_weights"] == 2


def test_centrality_weights_are_incidence_degrees() -> None:
    graph = Hypergraph(3, ((0, 1), (0, 2)))
    spec = ModelSpec(weights={"source": "centrality", "normalize": "max"})
    weights, _ = node_weights(spec, graph)
    np.testing.assert_allclose(weights, [1.0, 0.5, 0.5])


def test_custom_weights_override_graph_weights() -> None:
    graph = Hypergraph(2, ((0, 1),), weights=(1.0, 3.0))
    spec = ModelSpec(
        weights={"source": "custom", "custom": {"0": 1.0, "1": 1.0}, "normalize": "max"}
    )
    weights, _ = node_weights(spec, graph)
    np.testing.assert_allclose(weights, [1.0, 1.0])


def test_graph_weight_roundtrip(tmp_path) -> None:
    graph = Hypergraph(3, ((0, 1), (1, 2)), weights=(0.2, 0.4, 1.0))
    path = tmp_path / "graph.npz"
    save_graph(path, graph, np.array(graph.weights, dtype=np.float64))
    loaded, weights = load_graph(path)
    np.testing.assert_allclose(weights, [0.2, 0.4, 1.0])
    np.testing.assert_allclose(loaded.weights, [0.2, 0.4, 1.0])
