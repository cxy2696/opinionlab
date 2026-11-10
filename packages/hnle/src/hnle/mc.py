"""Monte-Carlo replicas with job-count-independent seeds (PRD OPT-22).

Replica seeds are spawned from one root ``SeedSequence`` before any work is
scheduled, so running with 1 job or 8 jobs yields identical replicas.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor

import numpy as np

from hnle.core.update import RunResult, run_simulation
from hnle.graph import Hypergraph
from hnle.spec import ModelSpec

_Job = tuple[ModelSpec, Hypergraph, int]


def replica_seeds(spec: ModelSpec, repeats: int) -> list[int]:
    """Derive one reproducible 64-bit seed per replica, independent of jobs."""
    root = np.random.SeedSequence(spec.seed)
    children = root.spawn(repeats)
    return [int(child.generate_state(1, dtype=np.uint64)[0]) for child in children]


def _run_job(job: _Job) -> RunResult:
    spec, graph, seed = job
    return run_simulation(spec, graph, seed)


def run_monte_carlo(
    spec: ModelSpec,
    graph: Hypergraph,
    repeats: int | None = None,
    jobs: int | None = None,
) -> list[RunResult]:
    """Run ``repeats`` replicas on ``jobs`` processes (results are order-stable)."""
    count = repeats if repeats is not None else spec.repeats
    if count < 1:
        raise ValueError("repeats: must be >= 1")
    seeds = replica_seeds(spec, count)
    payload: list[_Job] = [(spec, graph, seed) for seed in seeds]
    workers = jobs if jobs is not None else 1
    if workers > 1 and count > 1:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            return list(pool.map(_run_job, payload))
    return [_run_job(job) for job in payload]
