"""Student-t interval for censored per-replica metrics."""

from __future__ import annotations

import math

import numpy as np
from scipy.stats import t as student_t

from hnle.mc import censored_interval


def test_empty_values_are_json_safe() -> None:
    result = censored_interval([])
    assert result == {"mean": None, "ci95_lo": None, "ci95_hi": None, "n": 0}


def test_single_value_has_zero_width_interval() -> None:
    result = censored_interval([7.0])
    assert result["mean"] == 7.0
    assert result["ci95_lo"] == result["ci95_hi"] == 7.0
    assert result["n"] == 1


def test_interval_matches_student_t_not_normal() -> None:
    values = [float(value) for value in range(1, 11)]
    result = censored_interval(values)
    mean = sum(values) / len(values)
    sd = float(np.std(values, ddof=1))
    half = float(student_t.ppf(0.975, len(values) - 1)) * sd / math.sqrt(len(values))
    assert result["mean"] == mean
    assert math.isclose(float(result["ci95_lo"]), mean - half, rel_tol=1e-12)
    assert math.isclose(float(result["ci95_hi"]), mean + half, rel_tol=1e-12)
    assert result["n"] == 10
    # A normal approximation would be visibly narrower at df = 9.
    normal_half = 1.96 * sd / math.sqrt(len(values))
    assert half > normal_half
