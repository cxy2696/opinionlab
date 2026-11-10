"""Hypergraph construction helpers.

The full data-ingest pipeline (pseudonymisation, cleaning, five source shapes)
is implemented in hnle/ingest.py; this module only provides the in-memory hypergraph type and a
deterministic synthetic builder used by the engine and tests.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from hnle.spec import HyperedgeSpec


@dataclass(frozen=True)
class Hypergraph:
    """Immutable node/edge container; node ids are ``0..n_nodes-1``."""

    n_nodes: int
    hyperedges: tuple[tuple[int, ...], ...]
    initial_opinions: tuple[int, ...] | None = None

    def __post_init__(self) -> None:
        if self.n_nodes <= 0:
            raise ValueError("graph.n_nodes: must be positive")
        for edge in self.hyperedges:
            if len(edge) < 2:
                raise ValueError("graph.hyperedges: every hyperedge needs at least 2 nodes")
            if any(node < 0 or node >= self.n_nodes for node in edge):
                raise ValueError("graph.hyperedges: node id out of range")
        if self.initial_opinions is not None and len(self.initial_opinions) != self.n_nodes:
            raise ValueError("graph.initial_opinions: length must equal n_nodes")


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


def canonical_node_order(node_ids: Iterable[str]) -> list[str]:
    """Deterministic node ordering: unique then lexicographically sorted."""
    return sorted(set(node_ids))


def normalize_weights(
    raw: npt.NDArray[np.float64], *, all_zero_warning: str = "engagement_all_zero"
) -> tuple[npt.NDArray[np.float64], dict[str, int]]:
    """Scale weights to [0, 1]; all-zero input falls back to uniform + warning."""
    weights = np.asarray(raw, dtype=np.float64)
    warnings: dict[str, int] = {}
    peak = float(weights.max()) if weights.size else 0.0
    if peak <= 0.0:
        warnings[all_zero_warning] = 1
        return np.ones(weights.size, dtype=np.float64), warnings
    return weights / peak, warnings
