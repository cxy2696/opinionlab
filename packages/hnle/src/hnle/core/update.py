"""Node-centric synchronous update semantics.

Why this shape: the upstream prototype wrote ``new_opinions[node]`` and
``last_change_time[node]`` inside the hyperedge loop, so a node covered by
several hyperedges inherited the result and the timer of whichever hyperedge
happened to come last. Results therefore depended on hyperedge list order and
were not reproducible. Here every hyperedge probability is computed first, then
aggregated per node, then sampled once, and finally written back atomically at
the end of the step.

Randomness: every stream is derived from the caller's seed through
``SeedSequence.spawn`` (initial opinions, latencies, decisions). No module-level
RNG is touched, so results do not depend on process state or parallelism.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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
    WeightNormalize,
    WeightSource,
)

SeedLike = int | np.random.SeedSequence


@dataclass
class RunResult:
    """Outcome of one replica (series are group-level only)."""

    opinions: npt.NDArray[np.int64]
    steps: int
    diversity_series: list[float]
    cascade_series: list[float]
    time_to_consensus: int
    warn_counts: dict[str, int] = field(default_factory=dict)
    mean_opinion_series: list[float] = field(default_factory=list)
    max_latency: float = 0.0


def derive_streams(
    seed: SeedLike,
) -> tuple[np.random.Generator, np.random.Generator, np.random.Generator]:
    """Split a seed into independent init / latency / decision streams."""
    root = np.random.SeedSequence(seed) if isinstance(seed, int) else seed
    init_seq, latency_seq, decision_seq = root.spawn(3)
    return (
        np.random.default_rng(init_seq),
        np.random.default_rng(latency_seq),
        np.random.default_rng(decision_seq),
    )


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
    spec: ModelSpec,
    n_nodes: int,
    rng: np.random.Generator,
    data: tuple[int, ...] | None = None,
) -> npt.NDArray[np.int64]:
    """Initialise opinions from data or from the injected generator."""
    if spec.init_mode is InitMode.data_driven and data is not None:
        return np.asarray(data, dtype=np.int64)
    if spec.init_mode is InitMode.fixed_ratio:
        ones = int(round(spec.target_share_1 * n_nodes))
        opinions = np.zeros(n_nodes, dtype=np.int64)
        if ones:
            opinions[rng.choice(n_nodes, size=ones, replace=False)] = 1
        return opinions
    # data_driven without a dataset and balanced_random both draw uniformly; the
    # ingest layer supplies label-derived shares for real data.
    draws = rng.integers(0, spec.n_opinions, size=n_nodes, dtype=np.int64)
    return np.asarray(draws, dtype=np.int64)


def node_weights(
    spec: ModelSpec, graph: Hypergraph
) -> tuple[npt.NDArray[np.float64], dict[str, int]]:
    """Node influence weights, normalised per ``spec.weights``."""
    n_nodes = graph.n_nodes
    weights = np.ones(n_nodes, dtype=np.float64)
    warnings: dict[str, int] = {}
    if spec.weights.source is WeightSource.custom:
        custom = spec.weights.custom or {}
        weights = np.zeros(n_nodes, dtype=np.float64)
        for key, value in custom.items():
            index = int(key)
            if 0 <= index < n_nodes:
                weights[index] = value
        missing = int(np.count_nonzero(weights == 0.0))
        if missing:
            warnings["missing_node_weights"] = missing
    if spec.weights.normalize is WeightNormalize.max:
        peak = float(weights.max()) if weights.size else 0.0
        if peak > 0.0:
            weights = weights / peak
    elif spec.weights.normalize is WeightNormalize.zscore:
        std = float(weights.std())
        if std > 0.0:
            weights = (weights - weights.mean()) / std
    return weights, warnings


def edge_distributions(
    spec: ModelSpec,
    edges: tuple[tuple[int, ...], ...],
    opinions: npt.NDArray[np.int64],
    weights: npt.NDArray[np.float64],
) -> tuple[npt.NDArray[np.float64], int]:
    """``P_v(e)`` for every hyperedge; zero-total edges fall back to uniform."""
    k = spec.n_opinions
    scores = np.zeros((len(edges), k), dtype=np.float64)
    for edge_idx, edge in enumerate(edges):
        for node in edge:
            scores[edge_idx, opinions[node]] += weights[node]
    powered = np.power(scores, spec.q)
    denominator = powered.sum(axis=1)
    uniform = np.full((len(edges), k), 1.0 / k, dtype=np.float64)
    zero_edges = int(np.count_nonzero(denominator <= 0.0))
    merged = np.divide(
        powered,
        denominator[:, None],
        out=uniform.copy(),
        where=denominator[:, None] > 0,
    )
    return np.asarray(merged, dtype=np.float64), zero_edges


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


def choose_opinions(
    spec: ModelSpec,
    node_probs: npt.NDArray[np.float64],
    rng: np.random.Generator,
) -> npt.NDArray[np.int64]:
    """Apply the configured decision rule (one draw per active node)."""
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


def _reached_consensus(opinions: npt.NDArray[np.int64], spec: ModelSpec) -> bool:
    counts = np.bincount(opinions, minlength=spec.n_opinions)
    return bool(counts.max() / opinions.size >= spec.consensus_threshold)


def run_simulation(spec: ModelSpec, graph: Hypergraph, seed: SeedLike) -> RunResult:
    """Run one replica; all randomness derives from ``seed``."""
    # Canonical edge order makes aggregation bit-for-bit independent of the
    # order in which the caller supplied hyperedges (OPT-01 / G2).
    edges = tuple(sorted(graph.hyperedges))
    init_rng, latency_rng, decision_rng = derive_streams(seed)
    n_nodes = graph.n_nodes
    opinions = initial_opinions(spec, n_nodes, init_rng, graph.initial_opinions)
    latencies = draw_latencies(spec, n_nodes, latency_rng)
    weights, warn_counts = node_weights(spec, graph)
    last_change = np.zeros(n_nodes, dtype=np.int64)

    incident: list[list[int]] = [[] for _ in range(n_nodes)]
    for edge_idx, edge in enumerate(edges):
        for node in edge:
            incident[node].append(edge_idx)
    active = np.asarray([bool(ids) for ids in incident], dtype=bool)
    edge_sizes = np.asarray([len(edge) for edge in edges], dtype=np.float64)

    diversity_series = [diversity(opinions)]
    cascade_series: list[float] = []
    mean_opinion_series = [float(opinions.mean() / (spec.n_opinions - 1))]
    reached = _reached_consensus(opinions, spec)
    time_to_consensus = 0 if reached else -1

    for step in range(1, spec.n_steps + 1):
        edge_probs, zero_edges = edge_distributions(spec, edges, opinions, weights)
        if zero_edges:
            warn_counts["zero_denominator_edges"] = (
                warn_counts.get("zero_denominator_edges", 0) + zero_edges
            )
        node_probs = aggregate_node_probabilities(
            edge_probs, edge_sizes, incident, spec.aggregation
        )
        ready = ((step - last_change) >= latencies) & active
        new_opinions = opinions.copy()
        ready_idx = np.nonzero(ready)[0]
        if ready_idx.size:
            chosen = choose_opinions(spec, node_probs[ready_idx], decision_rng)
            new_opinions[ready_idx] = chosen
        changed = new_opinions != opinions
        last_change = cast("npt.NDArray[np.int64]", last_change.copy())
        last_change[changed] = step
        opinions = new_opinions

        cascade_series.append(float(np.count_nonzero(changed)) / n_nodes)
        diversity_series.append(diversity(opinions))
        mean_opinion_series.append(float(opinions.mean() / (spec.n_opinions - 1)))
        if time_to_consensus < 0 and _reached_consensus(opinions, spec):
            time_to_consensus = step

    return RunResult(
        opinions=opinions,
        steps=spec.n_steps,
        diversity_series=diversity_series,
        cascade_series=cascade_series,
        time_to_consensus=time_to_consensus,
        warn_counts=warn_counts,
        mean_opinion_series=mean_opinion_series,
        max_latency=float(latencies.max()) if latencies.size else 0.0,
    )
