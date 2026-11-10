"""US-004: node-centric aggregation, decision rules and latency gating."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from hnle.core.sparse import run_sparse
from hnle.core.update import aggregate_node_probabilities, edge_distributions, initial_opinions
from hnle.graph import Hypergraph
from hnle.spec import Aggregation, DecisionRule, ModelSpec


def _node_probs(
    aggregation: Aggregation,
) -> npt.NDArray[np.float64]:
    # nodes 0..2; edge 0 = (0,1), edge 1 = (0,1,2); opinions = [1,0,0]
    opinions = np.asarray([1, 0, 0], dtype=np.int64)
    spec = ModelSpec(q=1.0, n_opinions=2)
    edges = ((0, 1), (0, 1, 2))
    edge_probs, _ = edge_distributions(spec, edges, opinions, np.ones(3, dtype=np.float64))
    incident = [[0, 1], [0, 1], [1]]
    sizes = np.asarray([2.0, 3.0])
    return aggregate_node_probabilities(edge_probs, sizes, incident, aggregation)


def test_aggregation_mean_matches_hand_calculation() -> None:
    probs = _node_probs(Aggregation.mean)
    expected = (0.5 + 1.0 / 3.0) / 2.0
    assert probs[0, 1] == np.float64(expected)
    assert probs[2, 1] == np.float64(1.0 / 3.0)


def test_aggregation_max_takes_strongest_edge() -> None:
    probs = _node_probs(Aggregation.max)
    assert probs[0, 1] == np.float64(0.5)
    assert probs[2, 1] == np.float64(1.0 / 3.0)


def test_aggregation_size_weighted_uses_edge_sizes() -> None:
    probs = _node_probs(Aggregation.size_weighted)
    expected = (0.5 * 2.0 + (1.0 / 3.0) * 3.0) / 5.0
    assert probs[0, 1] == np.float64(expected)


def test_default_aggregation_is_mean() -> None:
    assert ModelSpec().aggregation is Aggregation.mean


def test_latency_gate_freezes_nodes_until_ready() -> None:
    graph = Hypergraph(n_nodes=2, hyperedges=((0, 1),))
    spec = ModelSpec(n_steps=3, latency={"dist": "const", "mu": 2})
    result = run_sparse(spec, graph, seed=1)
    # With a constant latency of 2 nothing can change before step 2.
    assert result.cascade_series[0] == 0.0


def test_argmax_is_deterministic_for_a_given_seed() -> None:
    graph = Hypergraph(n_nodes=40, hyperedges=tuple((i, i + 1, i + 2) for i in range(38)))
    spec = ModelSpec(
        n_steps=20,
        decision_rule=DecisionRule.argmax,
        n_opinions=2,
        latency={"dist": "const", "mu": 1},
        init_mode="data_driven",
    )
    first = run_sparse(spec, graph, seed=1)
    second = run_sparse(spec, graph, seed=1)
    np.testing.assert_array_equal(first.opinions, second.opinions)
    np.testing.assert_array_equal(first.diversity_series, second.diversity_series)


def test_threshold_rule_uses_spec_threshold() -> None:
    graph = Hypergraph(n_nodes=2, hyperedges=((0, 1),))
    spec = ModelSpec(
        n_steps=1,
        decision_rule=DecisionRule.threshold,
        threshold=0.9,
        latency={"dist": "const", "mu": 1},
        init_mode="fixed_ratio",
        target_share_1=1.0,
    )
    result = run_sparse(spec, graph, seed=2)
    # p1 = 1 on the edge, so both nodes become 1 under any threshold <= 1.
    assert result.opinions.tolist() == [1, 1]


def test_initial_opinions_fixed_ratio_share() -> None:
    rng = np.random.default_rng(0)
    spec = ModelSpec(init_mode="fixed_ratio", target_share_1=0.25)
    opinions = initial_opinions(spec, 40, rng)
    assert np.count_nonzero(opinions == 1) == 10
