"""Event-driven engine with latency clocks (PRD OPT-21).

Each node carries a clock; only nodes whose clock expires are evaluated, and
per-hyperedge opinion counts are maintained incrementally, so a batch touches
only the edges incident to the due nodes. This is where the speedup over the
dense discrete-step engine comes from.

Semantics: a node is re-scheduled ``L_i`` after every evaluation attempt
(continuous time supported when ``latency.quantize=continuous``). With
``L_i == 1`` this matches the synchronous sparse engine.
"""

from __future__ import annotations

import heapq
from typing import Any

import numpy as np
import numpy.typing as npt

from hnle.core.sparse import build_incidence
from hnle.core.update import (
    RunResult,
    choose_opinions,
    derive_streams,
    draw_latencies,
    initial_opinions,
    node_weights,
)
from hnle.graph import Hypergraph
from hnle.metrics import diversity
from hnle.spec import Aggregation, LatencyQuantize, ModelSpec


def _aggregate(
    spec: ModelSpec,
    probs: npt.NDArray[np.float64],
    rows: npt.NDArray[np.int64],
    lengths: npt.NDArray[np.int64],
    edge_weights: npt.NDArray[np.float64],
) -> npt.NDArray[np.float64]:
    """Aggregate per-incidence edge distributions onto their batch nodes."""
    n_batch = lengths.size
    k = probs.shape[1]
    if spec.aggregation is Aggregation.max:
        node_probs = np.zeros((n_batch, k), dtype=np.float64)
        np.maximum.at(node_probs, rows, probs)
        return node_probs

    gathered = probs * edge_weights[:, None] if edge_weights.size else probs
    columns = [
        np.bincount(rows, weights=gathered[:, opinion], minlength=n_batch)
        for opinion in range(k)
    ]
    sums = np.column_stack(columns)
    if edge_weights.size:
        denominators = np.bincount(rows, weights=edge_weights, minlength=n_batch)
    else:
        denominators = lengths.astype(np.float64)
    return np.asarray(
        np.divide(
            sums,
            denominators[:, None],
            out=np.full_like(sums, 1.0 / k),
            where=denominators[:, None] > 0,
        ),
        dtype=np.float64,
    )


def _process_batch(
    spec: ModelSpec,
    nodes: npt.NDArray[np.int64],
    opinions: npt.NDArray[np.int64],
    counts: npt.NDArray[np.float64],
    transposed: Any,
    edge_sizes: npt.NDArray[np.float64],
    decision_rng: np.random.Generator,
    warn_counts: dict[str, int],
) -> npt.NDArray[np.bool_]:
    """Evaluate one due batch in place; returns the changed mask."""
    k = spec.n_opinions
    batch_rows = transposed[nodes]
    lengths = np.diff(batch_rows.indptr).astype(np.int64)
    local_edges = batch_rows.indices.astype(np.int64)
    rows = np.repeat(np.arange(nodes.size, dtype=np.int64), lengths)

    # Duplicate edges (shared by several due nodes) are evaluated repeatedly,
    # which is cheaper than de-duplicating with a sort on small batches.
    scores = counts[local_edges]
    powered = np.power(scores, spec.q)
    denominator = powered.sum(axis=1)
    zero_edges = int(np.count_nonzero(denominator <= 0.0))
    uniform = np.full((local_edges.size, k), 1.0 / k, dtype=np.float64)
    probs = np.asarray(
        np.divide(
            powered,
            denominator[:, None],
            out=uniform.copy(),
            where=denominator[:, None] > 0,
        ),
        dtype=np.float64,
    )
    if zero_edges:
        warn_counts["zero_denominator_edges"] = (
            warn_counts.get("zero_denominator_edges", 0) + zero_edges
        )

    edge_weights = (
        edge_sizes[local_edges]
        if spec.aggregation is Aggregation.size_weighted
        else np.empty(0, dtype=np.float64)
    )
    node_probs = _aggregate(spec, probs, rows, lengths, edge_weights)
    chosen = choose_opinions(spec, node_probs, decision_rng)
    old = opinions[nodes]
    changed = chosen != old
    opinions[nodes] = chosen

    if changed.any():
        changed_nodes = nodes[changed]
        changed_rows = transposed[changed_nodes]
        changed_lengths = np.diff(changed_rows.indptr).astype(np.int64)
        changed_edges = changed_rows.indices.astype(np.int64)
        np.add.at(
            counts,
            (changed_edges, np.repeat(old[changed], changed_lengths).astype(np.int64)),
            -1.0,
        )
        np.add.at(
            counts,
            (changed_edges, np.repeat(chosen[changed], changed_lengths).astype(np.int64)),
            1.0,
        )
    return np.asarray(changed, dtype=np.bool_)


def run_event(spec: ModelSpec, graph: Hypergraph, seed: int) -> RunResult:
    """Run one replica with the event-driven kernel."""
    edges = tuple(sorted(graph.hyperedges))
    init_rng, latency_rng, decision_rng = derive_streams(seed)
    n_nodes = graph.n_nodes
    k = spec.n_opinions
    opinions = initial_opinions(spec, n_nodes, init_rng, graph.initial_opinions)
    latencies = draw_latencies(spec, n_nodes, latency_rng)
    weights, warn_counts = node_weights(spec, graph)

    incidence = build_incidence(graph, edges)
    transposed = incidence.T.tocsr()
    degree = np.asarray(transposed.sum(axis=1), dtype=np.float64).ravel()
    edge_sizes = np.asarray([len(edge) for edge in edges], dtype=np.float64)

    onehot = np.zeros((n_nodes, k), dtype=np.float64)
    onehot[np.arange(n_nodes), opinions] = 1.0
    counts = np.asarray(incidence @ onehot, dtype=np.float64)

    diversity_series = [diversity(opinions)]
    cascade_series: list[float] = []
    mean_opinion_series = [float(opinions.mean() / (k - 1))]
    time_to_consensus = 0 if _reached(opinions, spec) else -1
    horizon = float(spec.n_steps)
    active = [int(node) for node in np.nonzero(degree > 0)[0]]

    if spec.latency.quantize is LatencyQuantize.integer_steps:
        time_to_consensus = _run_bucketed(
            spec, active, latencies, opinions, counts, transposed, edge_sizes,
            decision_rng, warn_counts, diversity_series, cascade_series,
            mean_opinion_series, time_to_consensus, int(horizon),
        )
    else:
        time_to_consensus = _run_heap(
            spec, active, latencies, opinions, counts, transposed, edge_sizes,
            decision_rng, warn_counts, diversity_series, cascade_series,
            mean_opinion_series, time_to_consensus, horizon,
        )

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


def _record(
    spec: ModelSpec,
    opinions: npt.NDArray[np.int64],
    changed: npt.NDArray[np.bool_],
    now: float,
    diversity_series: list[float],
    cascade_series: list[float],
    mean_opinion_series: list[float],
    time_to_consensus: int,
) -> int:
    cascade_series.append(float(np.count_nonzero(changed)) / opinions.size)
    diversity_series.append(diversity(opinions))
    mean_opinion_series.append(float(opinions.mean() / (spec.n_opinions - 1)))
    if time_to_consensus < 0 and _reached(opinions, spec):
        return int(now)
    return time_to_consensus


def _run_bucketed(
    spec: ModelSpec,
    active: list[int],
    latencies: npt.NDArray[np.float64],
    opinions: npt.NDArray[np.int64],
    counts: npt.NDArray[np.float64],
    transposed: Any,
    edge_sizes: npt.NDArray[np.float64],
    decision_rng: np.random.Generator,
    warn_counts: dict[str, int],
    diversity_series: list[float],
    cascade_series: list[float],
    mean_opinion_series: list[float],
    time_to_consensus: int,
    horizon: int,
) -> int:
    buckets: list[list[int]] = [[] for _ in range(horizon + 1)]
    for node in active:
        first = max(int(latencies[node]), 1)
        if first <= horizon:
            buckets[first].append(node)

    for now in range(1, horizon + 1):
        if not buckets[now]:
            continue
        nodes = np.sort(np.asarray(buckets[now], dtype=np.int64))
        changed = _process_batch(
            spec, nodes, opinions, counts, transposed, edge_sizes,
            decision_rng, warn_counts,
        )
        time_to_consensus = _record(
            spec, opinions, changed, float(now), diversity_series,
            cascade_series, mean_opinion_series, time_to_consensus,
        )
        for node in nodes:
            next_time = now + max(int(latencies[node]), 1)
            if next_time <= horizon:
                buckets[next_time].append(int(node))
    return time_to_consensus


def _run_heap(
    spec: ModelSpec,
    active: list[int],
    latencies: npt.NDArray[np.float64],
    opinions: npt.NDArray[np.int64],
    counts: npt.NDArray[np.float64],
    transposed: Any,
    edge_sizes: npt.NDArray[np.float64],
    decision_rng: np.random.Generator,
    warn_counts: dict[str, int],
    diversity_series: list[float],
    cascade_series: list[float],
    mean_opinion_series: list[float],
    time_to_consensus: int,
    horizon: float,
) -> int:
    clock: list[tuple[float, int]] = [
        (max(float(latencies[node]), 1.0), node) for node in active
    ]
    heapq.heapify(clock)
    while clock and clock[0][0] <= horizon:
        now = clock[0][0]
        batch: list[int] = []
        while clock and clock[0][0] == now:
            _, node = heapq.heappop(clock)
            batch.append(node)
        nodes = np.sort(np.asarray(batch, dtype=np.int64))
        changed = _process_batch(
            spec, nodes, opinions, counts, transposed, edge_sizes,
            decision_rng, warn_counts,
        )
        time_to_consensus = _record(
            spec, opinions, changed, now, diversity_series, cascade_series,
            mean_opinion_series, time_to_consensus,
        )
        for node in nodes:
            heapq.heappush(clock, (now + max(float(latencies[node]), 1.0), int(node)))
    return time_to_consensus


def _reached(opinions: npt.NDArray[np.int64], spec: ModelSpec) -> bool:
    counts = np.bincount(opinions, minlength=spec.n_opinions)
    return bool(counts.max() / opinions.size >= spec.consensus_threshold)
