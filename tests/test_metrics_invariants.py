"""US-008: hypothesis invariants for metrics and the latency gate."""

from __future__ import annotations

import numpy as np
from hypothesis import given
from hypothesis import strategies as st
from numpy.testing import assert_allclose

from hnle.core.sparse import run_sparse
from hnle.graph import Hypergraph
from hnle.metrics import diversity, foster_polarization, opinion_shares, shannon_entropy
from hnle.spec import ModelSpec


@given(
    values=st.lists(st.integers(min_value=0, max_value=5), min_size=1, max_size=40),
    k=st.integers(min_value=2, max_value=6),
)
def test_metric_invariants(values: list[int], k: int) -> None:
    opinions = np.asarray([value % k for value in values], dtype=np.int64)
    shares = opinion_shares(opinions, k)
    assert_allclose(shares.sum(), 1.0, atol=1e-12)
    assert shares.min() >= 0.0
    assert np.isfinite(shares).all()

    value = diversity(opinions, k)
    assert 0.0 <= value <= 1.0 - 1.0 / k + 1e-12
    entropy = shannon_entropy(opinions, k)
    assert 0.0 <= entropy <= np.log2(k) + 1e-12
    polarization = foster_polarization(opinions, k)
    assert 0.0 <= polarization <= 1.0 + 1e-12


def test_unready_nodes_do_not_move() -> None:
    graph = Hypergraph(n_nodes=30, hyperedges=tuple((i, i + 1) for i in range(29)))
    spec = ModelSpec(
        n_steps=4,
        latency={"dist": "const", "mu": 5},
        init_mode="data_driven",
    )
    result = run_sparse(spec, graph, seed=2)
    assert result.cascade_series == [0.0, 0.0, 0.0, 0.0]
    assert result.diversity_series == [result.diversity_series[0]] * 5
