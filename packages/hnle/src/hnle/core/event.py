"""Event-driven engine with integer latency clocks.

Each node carries the next sweep at which it is due. A node that changes
opinion waits ``L_i`` sweeps; a node that does not change is due again on the
next sweep. This is the same clock rule as the discrete reference
(:mod:`hnle.core.update`) and the CSR engine: a node that keeps its opinion
stays eligible, while a node that changes is blocked for its latency. The
event kernel is exact for integer latencies; continuous latencies are handled
by the CSR engine.

Per-hyperedge weighted opinion counts are maintained incrementally, so a batch
only touches the edges incident to the due nodes. The series returned by this
engine are sampled on every integer sweep (with zero-change sweeps included),
which keeps them comparable with the CSR series and with the metrics that
assume a uniform time grid.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import numpy.typing as npt

from hnle.core.kernel import (
    conformity_probabilities,
    normalize_rows,
    ordinal_mean_opinion,
    reached_consensus,
)
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
from hnle.metrics import diversity, opinion_shares
from hnle.spec import Aggregation, LatencyQuantize, ModelSpec, TopologyMode


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
        # Element-wise max is not a distribution; normalise it before sampling.
        return normalize_rows(node_probs)

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
    weights: npt.NDArray[np.float64],
    transposed: Any,
    edge_sizes: npt.NDArray[np.float64],
    decision_rng: np.random.Generator,
    warn_counts: dict[str, int],
) -> npt.NDArray[np.bool_]:
    """Evaluate one due batch in place; returns the changed mask."""
    batch_rows = transposed[nodes]
    lengths = np.diff(batch_rows.indptr).astype(np.int64)
    local_edges = batch_rows.indices.astype(np.int64)
    rows = np.repeat(np.arange(nodes.size, dtype=np.int64), lengths)

    scores = counts[local_edges]
    probs, zero_edges = conformity_probabilities(scores, spec.q)
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
    current = opinions[nodes]
    chosen = choose_opinions(spec, node_probs, decision_rng, current)
    changed = chosen != current
    opinions[nodes] = chosen

    if changed.any():
        changed_nodes = nodes[changed]
        changed_rows = transposed[changed_nodes]
        changed_lengths = np.diff(changed_rows.indptr).astype(np.int64)
        changed_edges = changed_rows.indices.astype(np.int64)
        changed_weights = np.repeat(weights[changed_nodes], changed_lengths)
        np.add.at(
            counts,
            (changed_edges, np.repeat(current[changed], changed_lengths).astype(np.int64)),
            -changed_weights,
        )
        np.add.at(
            counts,
            (changed_edges, np.repeat(chosen[changed], changed_lengths).astype(np.int64)),
            changed_weights,
        )
    return np.asarray(changed, dtype=np.bool_)


def run_event(spec: ModelSpec, graph: Hypergraph, seed: int) -> RunResult:
    """Run one replica with the event-driven kernel."""
    if spec.shocks or spec.interventions:
        raise NotImplementedError(
            "event_driven engine does not support shocks/interventions yet"
        )
    if spec.topology.mode is not TopologyMode.static:
        raise NotImplementedError("event_driven engine requires static topology")
    if spec.latency.quantize is not LatencyQuantize.integer_steps:
        raise ValueError(
            "event_driven requires integer latency steps; use sparse_vector for "
            "continuous latency"
        )

    edges = tuple(sorted(graph.hyperedges))
    init_rng, latency_rng, decision_rng = derive_streams(seed)
    n_nodes = graph.n_nodes
    k = spec.n_opinions
    opinions = initial_opinions(spec, n_nodes, init_rng, graph.initial_opinions)
    latencies = draw_latencies(spec, n_nodes, latency_rng).astype(np.int64)
    weights, warn_counts = node_weights(spec, graph)

    incidence = build_incidence(graph, edges)
    transposed = incidence.T.tocsr()
    degree = np.asarray(transposed.sum(axis=1), dtype=np.float64).ravel()
    edge_sizes = np.asarray([len(edge) for edge in edges], dtype=np.float64)

    onehot = np.zeros((n_nodes, k), dtype=np.float64)
    onehot[np.arange(n_nodes), opinions] = 1.0
    counts = np.asarray(incidence @ (onehot * weights[:, None]), dtype=np.float64)

    diversity_series = [diversity(opinions)]
    cascade_series: list[float] = []
    mean_opinion_series = [ordinal_mean_opinion(opinions, k)]
    share_series = [opinion_shares(opinions, k).tolist()]
    time_to_consensus = 0 if reached_consensus(opinions, k, spec.consensus_threshold) else -1
    horizon = int(spec.n_steps)
    active = [int(node) for node in np.nonzero(degree > 0)[0]]

    buckets: list[list[int]] = [[] for _ in range(horizon + 1)]
    for node in active:
        first = max(int(latencies[node]), 1)
        if first <= horizon:
            buckets[first].append(node)

    for now in range(1, horizon + 1):
        changed = np.zeros(n_nodes, dtype=bool)
        if buckets[now]:
            nodes = np.sort(np.asarray(buckets[now], dtype=np.int64))
            batch_changed = _process_batch(
                spec, nodes, opinions, counts, weights, transposed, edge_sizes,
                decision_rng, warn_counts,
            )
            changed[nodes] = batch_changed
            for node, did_change in zip(nodes.tolist(), batch_changed.tolist(), strict=True):
                delay = max(int(latencies[node]), 1)
                next_time = now + (delay if did_change else 1)
                if next_time <= horizon:
                    buckets[next_time].append(int(node))

        cascade_series.append(float(np.count_nonzero(changed)) / n_nodes)
        diversity_series.append(diversity(opinions))
        mean_opinion_series.append(ordinal_mean_opinion(opinions, k))
        share_series.append(opinion_shares(opinions, k).tolist())
        if time_to_consensus < 0 and reached_consensus(
            opinions, k, spec.consensus_threshold
        ):
            time_to_consensus = now

    return RunResult(
        opinions=opinions,
        steps=spec.n_steps,
        diversity_series=diversity_series,
        cascade_series=cascade_series,
        time_to_consensus=time_to_consensus,
        warn_counts=warn_counts,
        mean_opinion_series=mean_opinion_series,
        max_latency=float(latencies.max()) if latencies.size else 0.0,
        share_series=share_series,
    )
