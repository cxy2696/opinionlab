"""Paired A/B comparison with bootstrap confidence intervals (OPT-35)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import numpy.typing as npt

from hnle.graph import Hypergraph
from hnle.mc import MetricCI, run_monte_carlo
from hnle.metrics import summarize
from hnle.spec import ModelSpec


@dataclass
class Comparison:
    metric: str
    baseline: MetricCI
    variant: MetricCI
    direction: str
    significant: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "baseline": self.baseline.to_dict(),
            "variant": self.variant.to_dict(),
            "direction": self.direction,
            "significant": self.significant,
        }


def bootstrap_ci(
    values: list[float] | npt.NDArray[np.float64],
    *,
    confidence: float = 0.95,
    iterations: int = 2000,
    seed: int = 0,
) -> tuple[float, float]:
    """Percentile bootstrap interval for the mean."""
    sample = np.asarray(values, dtype=np.float64)
    if sample.size == 0:
        return (0.0, 0.0)
    rng = np.random.default_rng(seed)
    means = np.empty(iterations, dtype=np.float64)
    for index in range(iterations):
        means[index] = rng.choice(sample, size=sample.size, replace=True).mean()
    alpha = (1.0 - confidence) / 2.0
    return (float(np.quantile(means, alpha)), float(np.quantile(means, 1.0 - alpha)))


def _metric_values(
    spec: ModelSpec,
    graph: Hypergraph,
    repeats: int,
    jobs: int,
    metric: str,
) -> list[float]:
    aggregate = run_monte_carlo(spec, graph, repeats=repeats, jobs=jobs, collect_raw=True)
    assert aggregate.raw is not None
    return [
        float(summarize(result, spec, graph.hyperedges).to_dict()[metric])
        for result in aggregate.raw
    ]


def compare_variants(
    spec: ModelSpec,
    graph: Hypergraph,
    variants: list[tuple[str, dict[str, Any]]],
    *,
    repeats: int = 20,
    jobs: int = 1,
    metric: str = "diversity_final",
    higher_is_better: bool = True,
) -> list[Comparison]:
    """Run baseline and variants on the same seed set and judge CI overlap."""
    baseline_values = _metric_values(spec, graph, repeats, jobs, metric)
    base_sample = np.asarray(baseline_values)
    base_ci = MetricCI(
        mean=float(base_sample.mean()),
        ci95_lo=bootstrap_ci(base_sample)[0],
        ci95_hi=bootstrap_ci(base_sample)[1],
        n=repeats,
    )

    results: list[Comparison] = []
    for name, overrides in variants:
        payload = spec.model_dump(mode="json")
        for key, value in overrides.items():
            parts = key.split(".")
            cursor = payload
            for part in parts[:-1]:
                cursor = cursor.setdefault(part, {})
            cursor[parts[-1]] = value
        candidate = ModelSpec.model_validate(payload)
        values = _metric_values(candidate, graph, repeats, jobs, metric)
        sample = np.asarray(values)
        variant_ci = MetricCI(
            mean=float(sample.mean()),
            ci95_lo=bootstrap_ci(sample)[0],
            ci95_hi=bootstrap_ci(sample)[1],
            n=repeats,
        )
        if variant_ci.ci95_lo > base_ci.ci95_hi:
            direction = "improved" if higher_is_better else "worsened"
            significant = True
        elif variant_ci.ci95_hi < base_ci.ci95_lo:
            direction = "worsened" if higher_is_better else "improved"
            significant = True
        else:
            direction = "inconclusive"
            significant = False
        results.append(
            Comparison(
                metric=metric,
                baseline=base_ci,
                variant=variant_ci,
                direction=f"{name}:{direction}" if name else direction,
                significant=significant,
            )
        )
    return results
