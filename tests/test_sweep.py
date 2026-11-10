"""grids, Latin hypercube, sensitivity ranking and calibration coverage."""

from __future__ import annotations

import numpy as np
import pandas as pd

from hnle.calibrate import calibrate, quantile_distance
from hnle.core.sparse import run_sparse
from hnle.graph import random_hypergraph
from hnle.spec import ModelSpec
from hnle.sweep import Axis, grid_samples, lhs_samples, parse_axis, sensitivity


def test_parse_axis_supports_ranges_and_lists() -> None:
    ranged = parse_axis("q=0.5:2.5:5")
    assert ranged.path == "q"
    np.testing.assert_allclose(ranged.values, np.linspace(0.5, 2.5, 5))
    listed = parse_axis("mu=1,5,10")
    assert listed.path == "latency.mu"
    assert listed.values == (1.0, 5.0, 10.0)


def test_grid_and_lhs_sample_counts() -> None:
    axes = [parse_axis("q=1:2:3"), parse_axis("sigma=1:3:2")]
    assert len(grid_samples(axes)) == 6
    lhs = lhs_samples(axes, 17, seed=4)
    assert len(lhs) == 17
    assert all(1.0 <= sample["q"] <= 2.0 for sample in lhs)
    assert all(1.0 <= sample["latency.sigma"] <= 3.0 for sample in lhs)


def test_sensitivity_ranks_the_dominant_parameter_first() -> None:
    frame = pd.DataFrame(
        {
            "q": np.linspace(0.5, 2.5, 20),
            "latency.mu": np.tile([1.0, 5.0], 10),
        }
    )
    frame["mean"] = frame["q"] * 0.3 + 0.01 * frame["latency.mu"]
    ranking = sensitivity(frame, ["q", "latency.mu"])
    assert ranking[0][0] == "q"
    assert ranking[0][1] > ranking[1][1]
    sobol = sensitivity(frame, ["q", "latency.mu"], method="sobol")
    assert sobol[0][0] == "q"


def test_quantile_distance_is_zero_for_identical_series() -> None:
    series = np.linspace(0.1, 0.5, 50)
    assert quantile_distance(series, series) == 0.0
    assert quantile_distance(series, series + 0.1) > 0.05


def test_calibration_coverage_at_least_80_percent() -> None:
    graph = random_hypergraph(80, 200, np.random.default_rng(11), ModelSpec().hyperedge)
    base = ModelSpec(n_steps=40, seed=1, q=1.5, latency={"dist": "const", "mu": 1})
    axis = Axis("q", tuple(float(value) for value in np.linspace(0.5, 2.5, 21)))
    covered = 0
    trials = 50
    for trial in range(trials):
        truth = 0.6 + 0.036 * trial
        truth_spec = ModelSpec.model_validate({**base.model_dump(), "q": truth})
        target = np.asarray(run_sparse(truth_spec, graph, seed=1).diversity_series)
        result = calibrate(base, graph, target, [axis], samples=20, seed=trial)
        low, high = result.intervals["q"]
        if low <= truth <= high:
            covered += 1
    assert covered / trials >= 0.8, covered
