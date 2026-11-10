"""Node-centric synchronous update semantics (PRD OPT-01).

Why this shape: the upstream prototype wrote ``new_opinions[node]`` and
``last_change_time[node]`` inside the hyperedge loop, so a node covered by
several hyperedges inherited the result and the timer of whichever hyperedge
happened to come last. Results therefore depended on hyperedge list order and
were not reproducible. Here every hyperedge probability is computed first, then
aggregated per node, then sampled once, and finally written back atomically at
the end of the step.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import numpy as np
import numpy.typing as npt

from hnle.graph import Hypergraph
from hnle.metrics import diversity
from hnle.spec import (
    Aggregation,
    DecisionRule,
    InitMode,
    LatencyDist,
    LatencyQuantize,
    ModelSpec,
)


@dataclass
class RunResult:
    """Outcome of one replica (series are group-level only)."""

    opinions: npt.NDArray[np.int64]
    steps: int
    diversity_series: list[float]
    cascade_series: list[float]
    time_to_consensus: int


def draw_latencies(
    spec: ModelSpec, n_nodes: int, rng: np.random.Generator
) -> npt.NDArray[np.float64]:
    """Per-node latency draws from the configured distribution."""
    latency = spec.latency
    draws: npt.NDArray[np.float64]
    if latency.dist is LatencyDist.const:
        draws = np.full(n_nodes, latency.mu, dtype=np.float64)
    elif latency.dist is LatencyDist.normal:
        draws = np.asarray(rng.normal(latency.mu, latency.sigma, n_nodes), dtype=np.float64)
    elif latency.dist is LatencyDist.lognormal:
        draws = np.asarray(rng.lognormal(latency.mu, latency.sigma, n_nodes), dtype=np.float64)
    else:
        if latency.lam is None:  # pragma: no cover - ModelSpec always fills this
            raise ValueError("latency.lambda: required for exponential latency")
        draws = np.asarray(rng.exponential(1.0 / latency.lam, n_nodes), dtype=np.float64)
    draws = np.maximum(draws, 0.0)
    if latency.quantize is LatencyQuantize.integer_steps:
        draws = np.rint(draws)
    return draws.astype(np.float64)


def initial_opinions(
    spec: ModelSpec, n_nodes: int, rng: np.random.Generator
) -> npt.NDArray[np.int64]:
    """Initialise opinions with the injected generator only."""
    if spec.init_mode is InitMode.fixed_ratio:
        ones = int(round(spec.target_share_1 * n_nodes))
        opinions = np.zeros(n_nodes, dtype=np.int64)
        if ones:
            opinions[rng.choice(n_nodes, size=ones, replace=False)] = 1
        return opinions
    if spec.init_mode is InitMode.balanced_random:
        draws = rng.integers(0, spec.n_opinions, size=n_nodes, dtype=np.int64)
        return np.asarray(draws, dtype=np.int64)
    # data_driven needs a dataset; synthetic graphs fall back to a balanced draw
    # until the ingest layer supplies label-derived shares (US-011).
    draws = rng.integers(0, spec.n_opinions, size=n_nodes, dtype=np.int64)
    return np.asarray(draws, dtype=np.int64)


def edge_distributions(
    spec: ModelSpec, edges: tuple[tuple[int, ...], ...], opinions: npt.NDArray[np.int64]
) -> npt.NDArray[np.float64]:
    """``P_v(e)`` for every hyperedge, computed before any node is updated."""
    k = spec.n_opinions
    counts = np.zeros((len(edges), k), dtype=np.float64)
    for edge_idx, edge in enumerate(edges):
        for node in edge:
            counts[edge_idx, opinions[node]] += 1.0
    powered = np.power(counts, spec.q)
    denominator = powered.sum(axis=1)
    uniform = np.full((len(edges), k), 1.0 / k, dtype=np.float64)
    merged = np.divide(
        powered,
        denominator[:, None],
        out=uniform.copy(),
        where=denominator[:, None] > 0,
    )
    return np.asarray(merged, dtype=np.float64)


def aggregate_node_probabilities(
    edge_probs: npt.NDArray[np.float64],
    edge_sizes: npt.NDArray[np.float64],
    incident: list[list[int]],
    aggregation: Aggregation,
) -> npt.NDArray[np.float64]:
    """Aggregate hyperedge distributions into one distribution per node."""
    n_nodes = len(incident)
    k = edge_probs.shape[1]
    node_probs = np.zeros((n_nodes, k), dtype=np.float64)
    for node, edge_ids in enumerate(incident):
        if not edge_ids:
            continue
        block = edge_probs[edge_ids]
        if aggregation is Aggregation.mean:
            node_probs[node] = block.mean(axis=0)
        elif aggregation is Aggregation.max:
            node_probs[node] = block.max(axis=0)
        else:
            sizes = edge_sizes[edge_ids]
            node_probs[node] = (block * sizes[:, None]).sum(axis=0) / sizes.sum()
    return node_probs


def _choose(
    spec: ModelSpec,
    node_probs: npt.NDArray[np.float64],
    rng: np.random.Generator,
) -> npt.NDArray[np.int64]:
    """Sample the next opinion for every active node (one draw per node)."""
    k = spec.n_opinions
    if spec.decision_rule is DecisionRule.argmax:
        return np.asarray(np.argmax(node_probs, axis=1), dtype=np.int64)
    if spec.decision_rule is DecisionRule.threshold:
        choice = np.zeros(node_probs.shape[0], dtype=np.int64)
        if k > 1:
            choice[node_probs[:, 1] >= spec.threshold] = 1
        return choice
    cdf = np.cumsum(node_probs, axis=1)
    cdf = cdf / cdf[:, -1:]
    draws = rng.random(node_probs.shape[0])[:, None]
    choice = np.sum(draws >= cdf, axis=1)
    return np.asarray(np.minimum(choice, k - 1), dtype=np.int64)


def _reached_consensus(
    opinions: npt.NDArray[np.int64], spec: ModelSpec
) -> bool:
    counts = np.bincount(opinions, minlength=spec.n_opinions)
    return bool(counts.max() / opinions.size >= spec.consensus_threshold)


def run_simulation(spec: ModelSpec, graph: Hypergraph, seed: int) -> RunResult:
    """Run one replica; all randomness derives from ``seed``."""
    # Canonical edge order makes aggregation bit-for-bit independent of the
    # order in which the caller supplied hyperedges (OPT-01 / G2).
    edges = tuple(sorted(graph.hyperedges))
    rng = np.random.default_rng(seed)
    n_nodes = graph.n_nodes
    opinions = initial_opinions(spec, n_nodes, rng)
    latencies = draw_latencies(spec, n_nodes, rng)
    last_change = np.zeros(n_nodes, dtype=np.int64)

    incident: list[list[int]] = [[] for _ in range(n_nodes)]
    for edge_idx, edge in enumerate(edges):
        for node in edge:
            incident[node].append(edge_idx)
    active = np.asarray([bool(ids) for ids in incident], dtype=bool)
    edge_sizes = np.asarray([len(edge) for edge in edges], dtype=np.float64)

    diversity_series = [diversity(opinions)]
    cascade_series: list[float] = []
    reached = _reached_consensus(opinions, spec)
    time_to_consensus = 0 if reached else -1

    for step in range(1, spec.n_steps + 1):
        edge_probs = edge_distributions(spec, edges, opinions)
        node_probs = aggregate_node_probabilities(
            edge_probs, edge_sizes, incident, spec.aggregation
        )
        ready = ((step - last_change) >= latencies) & active
        new_opinions = opinions.copy()
        ready_idx = np.nonzero(ready)[0]
        if ready_idx.size:
            chosen = _choose(spec, node_probs[ready_idx], rng)
            new_opinions[ready_idx] = chosen
        changed = new_opinions != opinions
        last_change = cast("npt.NDArray[np.int64]", last_change.copy())
        last_change[changed] = step
        opinions = new_opinions

        cascade_series.append(float(np.count_nonzero(changed)) / n_nodes)
        diversity_series.append(diversity(opinions))
        if time_to_consensus < 0 and _reached_consensus(opinions, spec):
            time_to_consensus = step
            reached = True

    return RunResult(
        opinions=opinions,
        steps=spec.n_steps,
        diversity_series=diversity_series,
        cascade_series=cascade_series,
        time_to_consensus=time_to_consensus,
    )
