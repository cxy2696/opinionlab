"""hypergraph canonicalisation: duplicate nodes and duplicate edges."""

from __future__ import annotations

import pytest

from hnle.graph import Hypergraph


def test_edges_are_sorted_and_deduplicated() -> None:
    graph = Hypergraph(
        n_nodes=4,
        hyperedges=((1, 0), (0, 1), (3, 2), (2, 3, 3)),
    )
    assert graph.hyperedges == ((0, 1), (2, 3))


def test_duplicate_node_ids_in_one_edge_are_reduced() -> None:
    graph = Hypergraph(n_nodes=3, hyperedges=((0, 0, 1),))
    assert graph.hyperedges == ((0, 1),)


def test_an_edge_with_one_distinct_node_is_rejected() -> None:
    with pytest.raises(ValueError):
        Hypergraph(n_nodes=3, hyperedges=((0, 0),))


def test_initial_opinions_length_is_validated() -> None:
    with pytest.raises(ValueError):
        Hypergraph(n_nodes=4, hyperedges=((0, 1),), initial_opinions=(0, 1))
