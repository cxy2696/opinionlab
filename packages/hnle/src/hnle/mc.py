"""Monte-Carlo replicas, Welford confidence intervals and memory guardrails.

Replica seeds are spawned from one root ``SeedSequence`` before any work is
scheduled, so running with 1 job or 8 jobs yields identical replicas. Curves are
only retained when explicitly requested; otherwise the aggregate is accumulated
incrementally (Welford) so large sweeps do not blow up memory.
"""

from __future__ import annotations

import math
import multiprocessing
import warnings
from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field

import numpy as np
from scipy.stats import t as student_t

from hnle.core.sparse import RunResult
from hnle.engine import run_engine
from hnle.graph import Hypergraph
from hnle.metrics import summarize
from hnle.spec import ModelSpec

_Job = tuple[ModelSpec, Hypergraph, int]
INSUFFICIENT_SAMPLES = 30


@dataclass
class MetricCI:
    """Mean and 95% t-interval for one aggregate metric."""

    mean: float
    ci95_lo: float
    ci95_hi: float
    n: int

    def to_dict(self) -> dict[str, float | int]:
        return {
            "mean": self.mean,
            "ci95_lo": self.ci95_lo,
            "ci95_hi": self.ci95_hi,
            "n": self.n,
        }


@dataclass
class AggregateResult:
    """Aggregated metrics over replicas, plus optional raw curves."""

    metrics: dict[str, MetricCI]
    n: int
    insufficient_samples: bool
    degraded_to_streaming: bool = False
    raw: list[RunResult] | None = field(default=None, repr=False)

    def to_dict(self) -> dict[str, object]:
        return {
            "metrics": {name: value.to_dict() for name, value in self.metrics.items()},
            "n": self.n,
            "insufficient_samples": self.insufficient_samples,
            "degraded_to_streaming": self.degraded_to_streaming,
        }


def censored_interval(
    values: Sequence[float], confidence: float = 0.95
) -> dict[str, float | int | None]:
    """Student-*t* interval for a metric that is defined per successful replica.

    Consensus time is censored: replicas that never reach a majority have no
    value and must be excluded from the mean, not counted as zero. The number
    of contributing replicas is returned separately so callers can report the
    censoring rate alongside the interval.

    ``n = 0`` returns all ``None`` values (JSON-safe); ``n = 1`` returns the
    single value with a zero-width interval.
    """
    data = [float(value) for value in values]
    count = len(data)
    if count == 0:
        return {"mean": None, "ci95_lo": None, "ci95_hi": None, "n": 0}
    mean = math.fsum(data) / count
    if count == 1:
        return {"mean": mean, "ci95_lo": mean, "ci95_hi": mean, "n": 1}
    variance = math.fsum((value - mean) ** 2 for value in data) / (count - 1)
    standard_error = math.sqrt(variance / count)
    critical = float(student_t.ppf(0.5 + confidence / 2.0, count - 1))
    return {
        "mean": mean,
        "ci95_lo": mean - critical * standard_error,
        "ci95_hi": mean + critical * standard_error,
        "n": count,
    }


class _Welford:
    """Numerically stable running mean/variance."""

    def __init__(self) -> None:
        self.n = 0
        self.mean = 0.0
        self.m2 = 0.0

    def add(self, value: float) -> None:
        self.n += 1
        delta = value - self.mean
        self.mean += delta / self.n
        self.m2 += delta * (value - self.mean)

    def interval(self, confidence: float = 0.95) -> tuple[float, float]:
        if self.n < 2:
            return (self.mean, self.mean)
        variance = self.m2 / (self.n - 1)
        standard_error = math.sqrt(variance / self.n)
        critical = float(student_t.ppf(0.5 + confidence / 2.0, self.n - 1))
        return (self.mean - critical * standard_error, self.mean + critical * standard_error)


def replica_seeds(spec: ModelSpec, repeats: int) -> list[int]:
    """Derive one reproducible 64-bit seed per replica, independent of jobs."""
    root = np.random.SeedSequence(spec.seed)
    children = root.spawn(repeats)
    return [int(child.generate_state(1, dtype=np.uint64)[0]) for child in children]


def _pool_context() -> multiprocessing.context.BaseContext:
    """Prefer fork where available: avoids re-importing the package per worker."""
    methods = multiprocessing.get_all_start_methods()
    if "fork" in methods:
        return multiprocessing.get_context("fork")
    return multiprocessing.get_context("spawn")


_WORKER_SPEC: ModelSpec | None = None
_WORKER_GRAPH: Hypergraph | None = None


def _init_worker(spec: ModelSpec, graph: Hypergraph) -> None:
    global _WORKER_SPEC, _WORKER_GRAPH
    _WORKER_SPEC = spec
    _WORKER_GRAPH = graph


def _run_seed(seed: int) -> RunResult:
    assert _WORKER_SPEC is not None and _WORKER_GRAPH is not None
    return run_engine(_WORKER_SPEC, _WORKER_GRAPH, seed)


def _run_job(job: _Job) -> RunResult:
    spec, graph, seed = job
    return run_engine(spec, graph, seed)


def _memory_estimate_bytes(spec: ModelSpec, graph: Hypergraph, repeats: int) -> int:
    # series are three float lists per step per replica; ~24 bytes per float
    return repeats * spec.n_steps * 24 * 3


def run_monte_carlo(
    spec: ModelSpec,
    graph: Hypergraph,
    repeats: int | None = None,
    jobs: int | None = None,
    *,
    collect_raw: bool = False,
    max_memory_gb: float | None = None,
) -> AggregateResult:
    """Run replicas, aggregate every metric and attach 95% confidence intervals."""
    count = repeats if repeats is not None else spec.repeats
    if count < 1:
        raise ValueError("repeats: must be >= 1")

    degraded = False
    keep_raw = collect_raw
    if keep_raw and max_memory_gb is not None:
        estimate = _memory_estimate_bytes(spec, graph, count)
        if estimate > max_memory_gb * 1e9:
            keep_raw = False
            degraded = True
            warnings.warn(
                "estimated memory exceeds max_memory_gb; aggregating streaming metrics only",
                RuntimeWarning,
                stacklevel=2,
            )

    seeds = replica_seeds(spec, count)
    payload: list[_Job] = [(spec, graph, seed) for seed in seeds]
    workers = jobs if jobs is not None else 1
    if workers > 1 and count > 1:
        with ProcessPoolExecutor(
            max_workers=workers,
            mp_context=_pool_context(),
            initializer=_init_worker,
            initargs=(spec, graph),
        ) as pool:
            results = list(pool.map(_run_seed, seeds))
    else:
        results = [_run_job(job) for job in payload]

    accumulators: dict[str, _Welford] = {}
    for result in results:
        summary = summarize(result, spec, graph.hyperedges).to_dict()
        for name, value in summary.items():
            accumulator = accumulators.setdefault(name, _Welford())
            accumulator.add(float(value))

    requested = {name.value for name in spec.metrics}
    metrics: dict[str, MetricCI] = {}
    for name, accumulator in accumulators.items():
        if name not in requested:
            continue
        low, high = accumulator.interval()
        metrics[name] = MetricCI(
            mean=accumulator.mean, ci95_lo=low, ci95_hi=high, n=accumulator.n
        )

    insufficient = count < INSUFFICIENT_SAMPLES
    if insufficient:
        warnings.warn(
            f"repeats={count} < {INSUFFICIENT_SAMPLES}: confidence intervals are underpowered",
            RuntimeWarning,
            stacklevel=2,
        )

    return AggregateResult(
        metrics=metrics,
        n=count,
        insufficient_samples=insufficient,
        degraded_to_streaming=degraded,
        raw=results if keep_raw else None,
    )
