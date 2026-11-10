"""Sparse engine placeholder (US-003 smoke path).

This is deliberately minimal: it proves the spec -> graph -> engine -> metric
pipeline and the reproducibility contract (injected ``Generator``, no global
RNG). US-004 replaces the update semantics with the node-centric, order-
invariant version and US-006 adds the CSR vectorisation.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from hnle.graph import Hypergraph
from hnle.spec import DecisionRule, InitMode, ModelSpec


@dataclass
class RunResult:
    """Final state of one replica; richer series arrive with US-008."""

    opinions: npt.NDArray[np.int64]
    steps: int


def initial_opinions(
    spec: ModelSpec, n_nodes: int, rng: np.random.Generator
) -> npt.NDArray[np.int64]:
    """Initialise opinions without touching global RNG state."""
    if spec.init_mode is InitMode.fixed_ratio:
        ones = int(round(spec.target_share_1 * n_nodes))
        opinions = np.zeros(n_nodes, dtype=np.int64)
        if ones:
            chosen = rng.choice(n_nodes, size=ones, replace=False)
            opinions[chosen] = 1
        return opinions
    # data_driven needs a dataset; synthetic graphs fall back to balanced_random
    # until the ingest layer (US-011) supplies label-derived shares.
    draws = rng.integers(0, spec.n_opinions, size=n_nodes, dtype=np.int64)
    return np.asarray(draws, dtype=np.int64)


def run_sparse(spec: ModelSpec, graph: Hypergraph, seed: int) -> RunResult:
    """Run ``n_steps`` synchronous updates and return the final population."""
    rng = np.random.default_rng(seed)
    opinions = initial_opinions(spec, graph.n_nodes, rng)

    incident: list[list[int]] = [[] for _ in range(graph.n_nodes)]
    for edge_idx, edge in enumerate(graph.hyperedges):
        for node in edge:
            incident[node].append(edge_idx)

    for _ in range(spec.n_steps):
        sums = np.zeros(graph.n_nodes, dtype=np.float64)
        counts = np.zeros(graph.n_nodes, dtype=np.float64)
        for edge in graph.hyperedges:
            members = np.asarray(edge, dtype=np.int64)
            ones = float(np.count_nonzero(opinions[members] == 1))
            zeros = float(members.size) - ones
            if ones <= 0.0 or zeros <= 0.0:
                p1 = 1.0 if zeros <= 0.0 else 0.0
            else:
                p1 = ones**spec.q / (ones**spec.q + zeros**spec.q)
            for node in edge:
                sums[node] += p1
                counts[node] += 1.0

        ready = counts > 0
        node_p = np.divide(
            sums,
            counts,
            out=np.full(graph.n_nodes, 0.5, dtype=np.float64),
            where=ready,
        )

        if spec.decision_rule is DecisionRule.argmax:
            candidates = (node_p > 0.5).astype(np.int64)
        elif spec.decision_rule is DecisionRule.threshold:
            candidates = (node_p >= spec.threshold).astype(np.int64)
        else:
            candidates = (rng.random(graph.n_nodes) < node_p).astype(np.int64)
        opinions = np.where(ready, candidates, opinions).astype(np.int64)

    return RunResult(opinions=opinions, steps=spec.n_steps)
