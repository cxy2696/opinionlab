"""the pytest + asyncio + numpy/scipy + pydantic combination works.

This is the first functional test by design: a spec, a 20-node
random hypergraph, the sparse placeholder engine and one metric.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from hnle.core.sparse import run_sparse
from hnle.graph import random_hypergraph
from hnle.metrics import diversity
from hnle.spec import ModelSpec


def test_spec_to_metric_smoke() -> None:
    spec = ModelSpec(n_steps=20, seed=7, q=2.0)
    rng = np.random.default_rng(spec.seed)
    graph = random_hypergraph(20, 30, rng, spec.hyperedge)

    result = run_sparse(spec, graph, spec.seed)

    assert result.opinions.shape == (20,)
    assert result.steps == 20
    value = diversity(result.opinions)
    assert 0.0 <= value <= 0.5
    assert np.count_nonzero(result.opinions == 0) + np.count_nonzero(result.opinions == 1) == 20


def test_same_seed_is_reproducible() -> None:
    spec = ModelSpec(n_steps=15, seed=11)
    graph = random_hypergraph(20, 25, np.random.default_rng(11), spec.hyperedge)
    first = run_sparse(spec, graph, seed=11)
    second = run_sparse(spec, graph, seed=11)
    np.testing.assert_array_equal(first.opinions, second.opinions)


def test_smoke_does_not_write_to_cwd() -> None:
    # The smoke path must stay pure: outputs go to the injected artifact dir only.
    before = set(Path.cwd().iterdir())
    spec = ModelSpec(n_steps=5, seed=3)
    graph = random_hypergraph(20, 10, np.random.default_rng(3), spec.hyperedge)
    run_sparse(spec, graph, spec.seed)
    assert set(Path.cwd().iterdir()) == before
