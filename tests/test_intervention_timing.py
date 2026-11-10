"""US-014: earlier debunk timing is distinguishable from later timing."""

from __future__ import annotations

import numpy as np

from hnle.compare import bootstrap_ci
from hnle.core.sparse import run_sparse
from hnle.graph import random_hypergraph
from hnle.mc import replica_seeds, run_monte_carlo
from hnle.metrics import summarize
from hnle.spec import ModelSpec


def _spec(at_step: int) -> ModelSpec:
    return ModelSpec(
        n_steps=60,
        seed=3,
        q=1.5,
        latency={"dist": "const", "mu": 1},
        repeats=30,
        interventions=[
            {
                "at_step": at_step,
                "type": "debunk",
                "target": {"opinion": "1"},
                "magnitude": 0.5,
                "duration": 1,
            }
        ],
    )


def _final_positive_share(spec: ModelSpec, graph: object) -> list[float]:
    aggregate = run_monte_carlo(spec, graph, repeats=30, collect_raw=True)
    assert aggregate.raw is not None
    return [
        float(summarize(result, spec, graph.hyperedges).to_dict()["avg_share_final"])
        for result in aggregate.raw
    ]


def test_debunk_timing_is_distinguishable() -> None:
    graph = random_hypergraph(300, 900, np.random.default_rng(3), _spec(2).hyperedge)
    early = _final_positive_share(_spec(2), graph)
    mid = _final_positive_share(_spec(12), graph)
    late = _final_positive_share(_spec(24), graph)

    assert np.mean(early) > np.mean(mid) >= np.mean(late), (
        np.mean(early), np.mean(mid), np.mean(late)
    )
    early_ci = bootstrap_ci(early)
    late_ci = bootstrap_ci(late)
    assert early_ci[0] > late_ci[1], (early_ci, late_ci)


def test_paired_seeds_are_shared() -> None:
    spec = _spec(2)
    seeds = replica_seeds(spec, 20)
    assert len(set(seeds)) == 20


def test_time_varying_topology_runs() -> None:
    spec = ModelSpec(
        n_steps=30,
        seed=4,
        topology={"mode": "time_varying", "arrival_rate": 1.0, "decay_rate": 0.05},
        latency={"dist": "const", "mu": 1},
    )
    graph = random_hypergraph(80, 160, np.random.default_rng(4), spec.hyperedge)
    result = run_sparse(spec, graph, seed=4)
    assert result.steps == 30
    assert np.isfinite(result.diversity_series).all()
