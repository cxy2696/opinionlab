"""Calibration of model parameters against a target series (PRD OPT-34)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from hnle.core.sparse import run_sparse
from hnle.graph import Hypergraph
from hnle.spec import ModelSpec
from hnle.sweep import Axis, lhs_samples, set_path


@dataclass
class CalibrationResult:
    best_params: dict[str, float]
    intervals: dict[str, tuple[float, float]]
    best_distance: float
    accepted: int

    def to_dict(self) -> dict[str, object]:
        return {
            "best_params": self.best_params,
            "intervals": {key: list(value) for key, value in self.intervals.items()},
            "best_distance": self.best_distance,
            "accepted": self.accepted,
        }


def quantile_distance(
    candidate: npt.NDArray[np.float64],
    target: npt.NDArray[np.float64],
    points: int = 16,
) -> float:
    """Mean absolute difference of quantiles (robust to length mismatches)."""
    length = min(candidate.size, target.size)
    if length == 0:
        return float("inf")
    quantiles = np.linspace(0.0, 1.0, points)
    left = np.quantile(candidate[:length], quantiles)
    right = np.quantile(target[:length], quantiles)
    return float(np.mean(np.abs(left - right)))


def calibrate(
    spec: ModelSpec,
    graph: Hypergraph,
    target: npt.NDArray[np.float64],
    axes: list[Axis],
    *,
    samples: int = 32,
    keep_ratio: float = 0.25,
    seed: int = 0,
    min_keep: int = 3,
) -> CalibrationResult:
    """Sample the parameter space and return credible intervals for accepted fits."""
    candidates = lhs_samples(axes, samples, seed=seed)
    scored: list[tuple[float, dict[str, float]]] = []
    for candidate in candidates:
        payload = spec.model_dump(mode="json")
        for path, value in candidate.items():
            set_path(payload, path, value)
        variant = ModelSpec.model_validate(payload)
        result = run_sparse(variant, graph, seed=variant.seed)
        curve = np.asarray(result.diversity_series, dtype=np.float64)
        scored.append((quantile_distance(curve, target), candidate))

    scored.sort(key=lambda item: item[0])
    keep = max(min_keep, int(round(len(scored) * keep_ratio)))
    accepted = scored[:keep]
    intervals: dict[str, tuple[float, float]] = {}
    for axis in axes:
        values = [candidate[axis.path] for _, candidate in accepted]
        intervals[axis.path] = (min(values), max(values))
    return CalibrationResult(
        best_params=dict(accepted[0][1]),
        intervals=intervals,
        best_distance=accepted[0][0],
        accepted=len(accepted),
    )
