"""US-014: shocks produce a cascade distinguishable from the baseline."""

from __future__ import annotations

import numpy as np

from hnle.compare import bootstrap_ci
from hnle.graph import random_hypergraph
from hnle.mc import run_monte_carlo
from hnle.spec import ModelSpec


def _case(with_shock: bool) -> ModelSpec:
    payload = {
        "n_steps": 60,
        "seed": 5,
        "q": 1.5,
        "latency": {"dist": "const", "mu": 1},
        "repeats": 12,
    }
    if with_shock:
        payload["shocks"] = [
            {"at_step": 10, "type": "flip_share", "magnitude": 0.4, "duration": 1}
        ]
    return ModelSpec.model_validate(payload)


def _cascade_at_shock(spec: ModelSpec, graph: object, repeats: int = 12) -> list[float]:
    aggregate = run_monte_carlo(spec, graph, repeats=repeats, collect_raw=True)
    assert aggregate.raw is not None
    # the forced flip lands on step 10 (index 9)
    return [float(result.cascade_series[9]) for result in aggregate.raw]


def test_shock_cascade_ci_does_not_overlap_baseline() -> None:
    graph = random_hypergraph(200, 600, np.random.default_rng(5), ModelSpec().hyperedge)
    baseline = _cascade_at_shock(_case(False), graph)
    shocked = _cascade_at_shock(_case(True), graph)
    base_lo, base_hi = bootstrap_ci(baseline)
    shock_lo, shock_hi = bootstrap_ci(shocked)
    assert shock_hi > base_hi and shock_lo > base_lo
    assert shock_lo > base_hi, (base_lo, base_hi, shock_lo, shock_hi)


def test_new_opinion_shock_changes_population() -> None:
    spec = ModelSpec(
        n_steps=5,
        q=1.0,
        latency={"dist": "const", "mu": 1},
        shocks=[{"at_step": 2, "type": "new_opinion", "magnitude": 0.4}],
    )
    graph = random_hypergraph(100, 200, np.random.default_rng(1), spec.hyperedge)
    from hnle.core.sparse import run_sparse

    result = run_sparse(spec, graph, seed=1)
    assert result.cascade_series[1] >= 0.4
