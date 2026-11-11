"""event-driven engine matches the sparse engine when L_i == 1."""

from __future__ import annotations

import numpy as np
import pytest
from pydantic import ValidationError
from scipy.stats import ks_2samp

from hnle.core.event import run_event
from hnle.core.sparse import run_sparse
from hnle.graph import random_hypergraph
from hnle.mc import replica_seeds
from hnle.spec import LatencyQuantize, ModelSpec


def _spec(quantize: LatencyQuantize = LatencyQuantize.integer_steps) -> ModelSpec:
    return ModelSpec(
        n_steps=60,
        seed=31,
        q=1.5,
        n_opinions=2,
        latency={"dist": "const", "mu": 1, "quantize": quantize},
    )


def test_unit_latency_distributions_are_equivalent() -> None:
    spec = _spec()
    graph = random_hypergraph(80, 160, np.random.default_rng(31), spec.hyperedge)
    seeds = replica_seeds(spec, 100)

    sparse_final = [run_sparse(spec, graph, seed).diversity_series[-1] for seed in seeds]
    event_final = [run_event(spec, graph, seed).diversity_series[-1] for seed in seeds]

    result = ks_2samp(sparse_final, event_final)
    assert result.pvalue > 0.05, result
    # With identical streams the two engines are in fact bit-identical.
    assert sparse_final == event_final


@pytest.mark.parametrize("latency", (2, 5))
def test_integer_latency_engines_are_equivalent(latency: int) -> None:
    payload = _spec().model_dump()
    payload["latency"] = {"dist": "const", "mu": latency}
    spec = ModelSpec.model_validate(payload)
    graph = random_hypergraph(50, 90, np.random.default_rng(17), spec.hyperedge)
    seeds = replica_seeds(spec, 20)
    for seed in seeds:
        sparse = run_sparse(spec, graph, seed)
        event = run_event(spec, graph, seed)
        np.testing.assert_allclose(sparse.diversity_series, event.diversity_series, atol=0.0)
        np.testing.assert_allclose(sparse.cascade_series, event.cascade_series, atol=0.0)
        np.testing.assert_array_equal(sparse.opinions, event.opinions)
        assert sparse.time_to_consensus == event.time_to_consensus


@pytest.mark.parametrize("aggregation", ("mean", "max", "size_weighted"))
def test_event_matches_sparse_for_every_aggregation(aggregation: str) -> None:
    payload = _spec().model_dump()
    payload["latency"] = {"dist": "const", "mu": 2}
    payload["aggregation"] = aggregation
    spec = ModelSpec.model_validate(payload)
    graph = random_hypergraph(50, 90, np.random.default_rng(29), spec.hyperedge)
    for seed in replica_seeds(spec, 10):
        sparse = run_sparse(spec, graph, seed)
        event = run_event(spec, graph, seed)
        np.testing.assert_allclose(sparse.diversity_series, event.diversity_series, atol=1e-12)
        np.testing.assert_allclose(sparse.cascade_series, event.cascade_series, atol=1e-12)
        np.testing.assert_array_equal(sparse.opinions, event.opinions)


def test_event_matches_sparse_with_custom_weights() -> None:
    payload = _spec().model_dump()
    payload["latency"] = {"dist": "const", "mu": 2}
    payload["weights"] = {
        "source": "custom",
        "custom": {str(i): float((i % 4) + 1) for i in range(50)},
    }
    spec = ModelSpec.model_validate(payload)
    graph = random_hypergraph(50, 90, np.random.default_rng(23), spec.hyperedge)
    for seed in replica_seeds(spec, 10):
        sparse = run_sparse(spec, graph, seed)
        event = run_event(spec, graph, seed)
        np.testing.assert_allclose(sparse.diversity_series, event.diversity_series, atol=1e-12)
        np.testing.assert_allclose(sparse.cascade_series, event.cascade_series, atol=1e-12)
        np.testing.assert_array_equal(sparse.opinions, event.opinions)


def test_event_engine_rejects_continuous_latency() -> None:
    payload = _spec(LatencyQuantize.continuous).model_dump()
    payload["engine"] = "event_driven"
    payload["latency"] = {"dist": "exponential", "mu": 3, "quantize": "continuous"}
    with pytest.raises(ValidationError):
        ModelSpec.model_validate(payload)

    # Continuous latency remains available through the CSR engine.
    sparse_payload = dict(payload)
    sparse_payload["engine"] = "sparse_vector"
    sparse_spec = ModelSpec.model_validate(sparse_payload)
    graph = random_hypergraph(60, 120, np.random.default_rng(8), sparse_spec.hyperedge)
    result = run_sparse(sparse_spec, graph, seed=8)
    assert result.opinions.shape == (60,)
    assert np.isfinite(result.diversity_series).all()
