"""US-004 golden baseline: upstream (order-dependent) semantics vs fixed engine.

The JSON file records both the legacy prototype behaviour and the node-centric
engine on the same graph/seed, so any future numeric drift is caught explicitly.
Regenerate only with ``UPDATE_GOLDEN=1`` and explain the change in the PR.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import numpy as np

from hnle.core.sparse import run_sparse
from hnle.core.update import draw_latencies, initial_opinions
from hnle.graph import Hypergraph, random_hypergraph
from hnle.metrics import diversity
from hnle.spec import ModelSpec

GOLDEN_PATH = Path(__file__).parent / "golden" / "pre_fix_baseline.json"


def _base() -> tuple[ModelSpec, Hypergraph]:
    spec = ModelSpec(
        n_steps=60,
        seed=3,
        q=1.5,
        n_opinions=2,
        latency={"dist": "const", "mu": 1},
        consensus_threshold=0.8,
    )
    graph = random_hypergraph(40, 80, np.random.default_rng(3), spec.hyperedge)
    return spec, graph


def _permuted(graph: Hypergraph, reverse: bool) -> Hypergraph:
    edges = tuple(reversed(graph.hyperedges)) if reverse else graph.hyperedges
    return Hypergraph(n_nodes=graph.n_nodes, hyperedges=edges)


def _legacy_run(spec: ModelSpec, graph: Hypergraph, seed: int) -> dict[str, float]:
    """Replica of the upstream prototype's in-place, order-dependent update."""
    rng = np.random.default_rng(seed)
    n_nodes = graph.n_nodes
    opinions = initial_opinions(spec, n_nodes, rng)
    latencies = draw_latencies(spec, n_nodes, rng)
    last_change = np.zeros(n_nodes, dtype=np.int64)
    cascade: list[float] = []
    reached = max(np.bincount(opinions).max() / n_nodes, 0.0) >= spec.consensus_threshold
    time_to_consensus = 0 if reached else -1

    for step in range(1, spec.n_steps + 1):
        new_opinions = opinions.copy()
        for edge in graph.hyperedges:  # order matters: later edges overwrite earlier ones
            members = np.asarray(edge, dtype=np.int64)
            ones = float(np.count_nonzero(opinions[members] == 1))
            zeros = float(members.size) - ones
            p1 = 1.0 if zeros <= 0.0 else (0.0 if ones <= 0.0 else ones**spec.q / (
                ones**spec.q + zeros**spec.q
            ))
            for node in edge:
                if step - last_change[node] < latencies[node]:
                    continue
                new_opinions[node] = 1 if rng.random() < p1 else 0
                last_change[node] = step  # upstream bug: timer reset before atomic writeback
        changed = new_opinions != opinions
        opinions = new_opinions
        cascade.append(float(np.count_nonzero(changed)) / n_nodes)
        if time_to_consensus < 0 and max(np.bincount(opinions).max() / n_nodes, 0.0) >= (
            spec.consensus_threshold
        ):
            time_to_consensus = step

    return {
        "diversity_final": diversity(opinions),
        "time_to_consensus": float(time_to_consensus),
        "cascade_mean": float(np.mean(cascade)) if cascade else 0.0,
    }


def _fixed_run(spec: ModelSpec, graph: Hypergraph, seed: int) -> dict[str, float]:
    result = run_sparse(spec, graph, seed)
    return {
        "diversity_final": result.diversity_series[-1],
        "time_to_consensus": float(result.time_to_consensus),
        "cascade_mean": float(np.mean(result.cascade_series)) if result.cascade_series else 0.0,
    }


def _compute() -> dict[str, Any]:
    spec, graph = _base()
    reverse = _permuted(graph, reverse=True)
    return {
        "note": (
            "US-004 golden baseline. 'upstream' replicates the in-place, order-dependent "
            "hyperedge loop; 'fixed' is the node-centric engine. Regenerate only with "
            "UPDATE_GOLDEN=1 and explain the numeric change."
        ),
        "config": spec.model_dump(mode="json"),
        "upstream": {
            "identity": _legacy_run(spec, graph, spec.seed),
            "reversed": _legacy_run(spec, reverse, spec.seed),
        },
        "fixed": {
            "identity": _fixed_run(spec, graph, spec.seed),
            "reversed": _fixed_run(spec, reverse, spec.seed),
        },
    }


def test_pre_fix_baseline() -> None:
    computed = _compute()
    if os.environ.get("UPDATE_GOLDEN") == "1":
        GOLDEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN_PATH.write_text(json.dumps(computed, indent=2, ensure_ascii=False) + "\n")
        return
    expected = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    for variant in ("identity", "reversed"):
        for family in ("upstream", "fixed"):
            for key, value in expected[family][variant].items():
                np.testing.assert_allclose(
                    computed[family][variant][key],
                    value,
                    atol=1e-12,
                    err_msg=f"{family}/{variant}/{key}",
                )

    upstream = expected["upstream"]
    upstream_gap = any(
        abs(upstream["identity"][key] - upstream["reversed"][key]) > 1e-12
        for key in upstream["identity"]
    )
    fixed = expected["fixed"]
    fixed_gap = any(
        abs(fixed["identity"][key] - fixed["reversed"][key]) > 0.0 for key in fixed["identity"]
    )
    assert upstream_gap, "baseline must demonstrate the upstream order-dependence defect"
    assert not fixed_gap, "node-centric engine must be permutation invariant"


def test_golden_is_deterministic() -> None:
    first = _compute()
    second = _compute()
    assert first == second
