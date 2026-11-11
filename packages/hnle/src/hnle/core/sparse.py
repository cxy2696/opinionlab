"""CSR-vectorised sparse engine.

``H`` is the (n_edges x n_nodes) incidence matrix. One step becomes:

    scores = H @ (W * onehot(opinions))          # S_v(e) for every opinion v
    P      = scores**q / sum_v scores**q          # per hyperedge distribution
    p_node = aggregate_{e contains i}(P(e))      # mean | max | size_weighted

All of it is sparse matrix algebra, so a step costs ``O(nnz(H) * k)`` instead
of the upstream nested Python loops. The node-centric semantics, RNG contract
and decision rules are shared with :mod:`hnle.core.update`, which stays in the
tree as the readable reference implementation used by the equivalence test.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import numpy.typing as npt
from scipy.sparse import csr_matrix

from hnle.core.kernel import (
    conformity_probabilities,
    normalize_rows,
    ordinal_mean_opinion,
    reached_consensus,
)
from hnle.core.shocks import apply_one_shot, evolve_topology, probability_bias
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
from hnle.spec import Aggregation, ModelSpec, TopologyMode

__all__ = ["RunResult", "build_incidence", "run_sparse"]


def build_incidence(
    graph: Hypergraph, edges: tuple[tuple[int, ...], ...] | None = None
) -> Any:
    """Build the CSR incidence matrix ``H[edge, node] = 1``."""
    chosen = edges if edges is not None else graph.hyperedges
    lengths = np.fromiter((len(edge) for edge in chosen), dtype=np.int64, count=len(chosen))
    rows = np.repeat(np.arange(len(chosen), dtype=np.int64), lengths)
    cols = np.fromiter(
        (node for edge in chosen for node in edge), dtype=np.int64, count=int(lengths.sum())
    )
    data = np.ones(cols.size, dtype=np.float64)
    return csr_matrix((data, (rows, cols)), shape=(len(chosen), graph.n_nodes))


def _node_probabilities(
    spec: ModelSpec,
    incidence: Any,
    transposed: Any,
    degree: npt.NDArray[np.float64],
    edge_sizes: npt.NDArray[np.float64],
    opinions: npt.NDArray[np.int64],
    weights: npt.NDArray[np.float64],
) -> tuple[npt.NDArray[np.float64], int]:
    """Vectorised P_v(e) plus node aggregation; returns (p_node, zero_edges)."""
    n_nodes = opinions.size
    k = spec.n_opinions
    onehot = np.zeros((n_nodes, k), dtype=np.float64)
    onehot[np.arange(n_nodes), opinions] = 1.0
    scores = np.asarray(incidence @ (onehot * weights[:, None]), dtype=np.float64)

    edge_probs, zero_edges = conformity_probabilities(scores, spec.q)

    if spec.aggregation is Aggregation.max:
        coo = transposed.tocoo()
        node_probs = np.zeros((n_nodes, k), dtype=np.float64)
        np.maximum.at(node_probs, coo.row, edge_probs[coo.col])
        return normalize_rows(node_probs), zero_edges

    if spec.aggregation is Aggregation.size_weighted:
        numerator = np.asarray(
            transposed @ (edge_probs * edge_sizes[:, None]), dtype=np.float64
        )
        denominator_nodes = np.asarray(transposed @ edge_sizes, dtype=np.float64).ravel()
    else:
        numerator = np.asarray(transposed @ edge_probs, dtype=np.float64)
        denominator_nodes = degree

    node_probs = np.divide(
        numerator,
        denominator_nodes[:, None],
        out=np.zeros_like(numerator),
        where=denominator_nodes[:, None] > 0,
    )
    return np.asarray(node_probs, dtype=np.float64), zero_edges


def run_sparse(spec: ModelSpec, graph: Hypergraph, seed: int) -> RunResult:
    """Run one replica with the CSR kernel."""
    edge_list: list[tuple[int, ...]] = list(sorted(graph.hyperedges))
    init_rng, latency_rng, decision_rng = derive_streams(seed)
    n_nodes = graph.n_nodes
    k = spec.n_opinions
    opinions = initial_opinions(spec, n_nodes, init_rng, graph.initial_opinions)
    latencies = draw_latencies(spec, n_nodes, latency_rng)
    weights, warn_counts = node_weights(spec, graph)

    def rebuild() -> tuple[Any, Any, npt.NDArray[np.float64], npt.NDArray[np.float64]]:
        current = tuple(edge_list)
        matrix = build_incidence(graph, current)
        matrix_t = matrix.T.tocsr()
        deg = np.asarray(matrix_t.sum(axis=1), dtype=np.float64).ravel()
        sizes = np.asarray([len(edge) for edge in current], dtype=np.float64)
        return matrix, matrix_t, deg, sizes

    incidence, transposed, degree, edge_sizes = rebuild()
    last_change = np.zeros(n_nodes, dtype=np.int64)

    diversity_series = [diversity(opinions)]
    cascade_series: list[float] = []
    mean_opinion_series = [ordinal_mean_opinion(opinions, k)]
    share_series = [opinion_shares(opinions, k).tolist()]
    time_to_consensus = 0 if _reached(opinions, spec) else -1

    active = degree > 0
    step_range = range(1, spec.n_steps + 1)
    for step in step_range:
        before = opinions.copy()
        if spec.topology.mode is TopologyMode.time_varying:
            edge_list, _added, _removed = evolve_topology(
                spec, edge_list, n_nodes, decision_rng
            )
            incidence, transposed, degree, edge_sizes = rebuild()
            active = degree > 0
        forced = apply_one_shot(spec, opinions, step, decision_rng)
        node_probs, zero_edges = _node_probabilities(
            spec, incidence, transposed, degree, edge_sizes, opinions, weights
        )
        bias = probability_bias(spec, step)
        if bias:
            if k != 2:
                raise ValueError("probability bias interventions require n_opinions=2")
            shifted = np.clip(node_probs[:, 1] + bias, 0.0, 1.0)
            node_probs = np.column_stack([1.0 - shifted, shifted])
        if zero_edges:
            warn_counts["zero_denominator_edges"] = (
                warn_counts.get("zero_denominator_edges", 0) + zero_edges
            )
        ready = ((step - last_change) >= latencies) & active
        new_opinions = opinions.copy()
        ready_idx = np.nonzero(ready)[0]
        if ready_idx.size:
            new_opinions[ready_idx] = choose_opinions(
                spec, node_probs[ready_idx], decision_rng, opinions[ready_idx]
            )
        changed = (new_opinions != before) | forced
        last_change[changed] = step
        opinions = new_opinions

        cascade_series.append(float(np.count_nonzero(changed)) / n_nodes)
        diversity_series.append(diversity(opinions))
        mean_opinion_series.append(ordinal_mean_opinion(opinions, k))
        share_series.append(opinion_shares(opinions, k).tolist())
        if time_to_consensus < 0 and _reached(opinions, spec):
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
        share_series=share_series,
    )


def _reached(opinions: npt.NDArray[np.int64], spec: ModelSpec) -> bool:
    return reached_consensus(opinions, spec.n_opinions, spec.consensus_threshold)
