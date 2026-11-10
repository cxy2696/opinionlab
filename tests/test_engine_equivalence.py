"""US-007: event-driven engine matches the sparse engine when L_i == 1."""

from __future__ import annotations

import numpy as np
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


def test_event_engine_supports_continuous_latency() -> None:
    payload = _spec(LatencyQuantize.continuous).model_dump()
    payload["engine"] = "event_driven"
    payload["latency"] = {"dist": "exponential", "mu": 3, "quantize": "continuous"}
    spec = ModelSpec.model_validate(payload)
    graph = random_hypergraph(60, 120, np.random.default_rng(8), spec.hyperedge)
    result = run_event(spec, graph, seed=8)
    assert result.opinions.shape == (60,)
    assert np.isfinite(result.diversity_series).all()
