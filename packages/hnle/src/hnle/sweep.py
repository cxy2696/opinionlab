"""Parameter sweeps and sensitivity ranking (PRD OPT-34).

Supports full grids and Latin-hypercube samples. Sensitivity defaults to
Pearson correlation; ``method="sobol"`` reports a first-order variance effect
(eta-squared over quantile bins), which is cheap and works for both grids and
LHS samples without an extra dependency.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
import numpy.typing as npt
import pandas as pd

from hnle.graph import Hypergraph
from hnle.mc import run_monte_carlo
from hnle.spec import ModelSpec

PARAM_ALIASES = {
    "mu": "latency.mu",
    "sigma": "latency.sigma",
    "lambda": "latency.lambda",
    "r": "consensus_threshold",
    "threshold": "consensus_threshold",
    "max_size": "hyperedge.max_size",
    "min_size": "hyperedge.min_size",
}
AXIS_PATHS = (
    "q",
    "latency.mu",
    "latency.sigma",
    "consensus_threshold",
    "hyperedge.max_size",
    "hyperedge.min_size",
    "n_steps",
)


@dataclass(frozen=True)
class Axis:
    path: str
    values: tuple[float, ...]


def normalise_path(path: str) -> str:
    return PARAM_ALIASES.get(path.strip(), path.strip())


def parse_axis(item: str) -> Axis:
    """Parse ``q=0.5:2.5:5`` (start:end:count) or ``q=1,1.5,2``."""
    key, separator, raw = item.partition("=")
    if not separator or not key:
        raise ValueError(f"axis expects key=values, got {item!r}")
    path = normalise_path(key)
    values: tuple[float, ...]
    if ":" in raw:
        start, end, count = (float(part) for part in raw.split(":"))
        if count < 2:
            values = (start,)
        else:
            values = tuple(float(value) for value in np.linspace(start, end, int(count)))
    else:
        values = tuple(float(part) for part in raw.split(",") if part.strip())
    if not values:
        raise ValueError(f"axis {path!r} has no values")
    return Axis(path=path, values=values)


def set_path(payload: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    cursor = payload
    for part in parts[:-1]:
        nested = cursor.get(part)
        if not isinstance(nested, dict):
            nested = {}
            cursor[part] = nested
        cursor = nested
    cursor[parts[-1]] = value


def grid_samples(axes: list[Axis]) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for combination in itertools.product(*(axis.values for axis in axes)):
        samples.append({axis.path: value for axis, value in zip(axes, combination, strict=True)})
    return samples


def lhs_samples(axes: list[Axis], count: int, seed: int = 0) -> list[dict[str, Any]]:
    """Latin-hypercube samples within each axis range."""
    if count < 1:
        raise ValueError("lhs sample count must be >= 1")
    rng = np.random.default_rng(seed)
    columns: list[npt.NDArray[np.float64]] = []
    for axis in axes:
        low, high = min(axis.values), max(axis.values)
        strata = (np.arange(count) + rng.random(count)) / count
        columns.append(low + strata * (high - low))
    return [
        {axis.path: float(column[index]) for axis, column in zip(axes, columns, strict=True)}
        for index in range(count)
    ]


def _variant(spec: ModelSpec, sample: dict[str, Any]) -> ModelSpec:
    payload = spec.model_dump(mode="json")
    for path, value in sample.items():
        set_path(payload, path, value)
    return ModelSpec.model_validate(payload)


def run_sweep(
    spec: ModelSpec,
    graph: Hypergraph,
    samples: list[dict[str, Any]],
    *,
    repeats: int = 1,
    jobs: int = 1,
    metric: str = "diversity_final",
) -> pd.DataFrame:
    """Run every sample and return a phase-diagram dataframe."""
    rows: list[dict[str, Any]] = []
    for sample in samples:
        variant = _variant(spec, sample)
        aggregate = run_monte_carlo(variant, graph, repeats=repeats, jobs=jobs)
        interval = aggregate.metrics[metric]
        rows.append(
            {
                **sample,
                "metric": metric,
                "mean": interval.mean,
                "ci95_lo": interval.ci95_lo,
                "ci95_hi": interval.ci95_hi,
                "n": interval.n,
                "q": variant.q,
            }
        )
    return pd.DataFrame(rows)


def sensitivity(
    frame: pd.DataFrame,
    parameters: list[str],
    metric_column: str = "mean",
    method: Literal["pearson", "sobol"] = "pearson",
) -> list[tuple[str, float]]:
    """Rank parameters by influence on the chosen metric."""
    target = frame[metric_column].to_numpy(dtype=np.float64)
    if target.size < 2 or np.std(target) == 0.0:
        return [(name, 0.0) for name in parameters]
    scores: list[tuple[str, float]] = []
    for name in parameters:
        values = frame[name].to_numpy(dtype=np.float64)
        if np.std(values) == 0.0:
            scores.append((name, 0.0))
            continue
        if method == "pearson":
            score = float(abs(np.corrcoef(values, target)[0, 1]))
        else:
            score = _first_order_effect(values, target)
        scores.append((name, score))
    return sorted(scores, key=lambda item: item[1], reverse=True)


def _first_order_effect(
    values: npt.NDArray[np.float64],
    target: npt.NDArray[np.float64],
    bins: int = 8,
) -> float:
    """Eta-squared: between-bin variance share of the target (1st-order proxy)."""
    edges = np.quantile(values, np.linspace(0.0, 1.0, bins + 1))
    edges = np.unique(edges)
    if edges.size <= 2:
        return 0.0
    indices = np.clip(np.digitize(values, edges[1:-1]), 0, edges.size - 2)
    total_var = float(np.var(target))
    if total_var <= 0.0:
        return 0.0
    between = 0.0
    for group in range(int(indices.max()) + 1):
        mask = indices == group
        if np.any(mask):
            between += mask.sum() * (float(np.mean(target[mask])) - float(np.mean(target))) ** 2
    return float(between / (target.size * total_var))
