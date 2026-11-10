"""Hypergraph construction helpers.

The full data-ingest pipeline (pseudonymisation, cleaning, five source shapes)
lands in US-011; this module only provides the in-memory hypergraph type and a
deterministic synthetic builder used by the engine and tests.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from hnle.spec import HyperedgeSpec


@dataclass(frozen=True)
class Hypergraph:
    """Immutable node/edge container; node ids are ``0..n_nodes-1``."""

    n_nodes: int
    hyperedges: tuple[tuple[int, ...], ...]

    def __post_init__(self) -> None:
        if self.n_nodes <= 0:
            raise ValueError("graph.n_nodes: must be positive")
        for edge in self.hyperedges:
            if len(edge) < 2:
                raise ValueError("graph.hyperedges: every hyperedge needs at least 2 nodes")
            if any(node < 0 or node >= self.n_nodes for node in edge):
                raise ValueError("graph.hyperedges: node id out of range")


def random_hypergraph(
    n_nodes: int,
    n_edges: int,
    rng: np.random.Generator,
    cfg: HyperedgeSpec | None = None,
) -> Hypergraph:
    """Build a seeded random hypergraph with edge sizes inside ``cfg`` bounds."""
    spec = cfg or HyperedgeSpec()
    if n_nodes < spec.min_size:
        raise ValueError(
            f"graph.n_nodes: {n_nodes} is smaller than hyperedge.min_size={spec.min_size}"
        )
    max_size = min(spec.max_size, n_nodes)
    edges: list[tuple[int, ...]] = []
    for _ in range(n_edges):
        size = int(rng.integers(spec.min_size, max_size + 1))
        members = rng.choice(n_nodes, size=size, replace=False)
        edges.append(tuple(sorted(int(node) for node in members)))
    return Hypergraph(n_nodes=n_nodes, hyperedges=tuple(edges))


def adjacency_lists(graph: Hypergraph) -> list[list[int]]:
    """Return, for every node, the indices of hyperedges that contain it."""
    incident: list[list[int]] = [[] for _ in range(graph.n_nodes)]
    for edge_idx, edge in enumerate(graph.hyperedges):
        for node in edge:
            incident[node].append(edge_idx)
    return incident


def opinions_array(opinions: list[int]) -> npt.NDArray[np.int64]:
    """Validate a plain list of opinions and convert it to an ``int64`` array."""
    return np.asarray(opinions, dtype=np.int64)
