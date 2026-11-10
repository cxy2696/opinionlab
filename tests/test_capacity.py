"""capacity formula and locust scenarios."""

from __future__ import annotations

from pathlib import Path

import pytest

from hnle.capacity import (
    DEFAULT_C,
    calibrated_c,
    job_seconds,
    single_replica_seconds,
    theoretical_jobs_per_second,
    worker_slots,
)

ROOT = Path(__file__).parents[1]


def test_single_replica_and_job_formulas() -> None:
    one = single_replica_seconds(1_200_000, 500)
    assert one == pytest.approx(DEFAULT_C * 1_200_000 * 500)
    job = job_seconds(1_200_000, 500, repeats=50, jobs=8)
    assert job == pytest.approx(one * 50 / 8)
    with pytest.raises(ValueError):
        job_seconds(100, 10, repeats=1, jobs=0)


def test_calibrated_c_from_benchmark_numbers() -> None:
    c_10k = calibrated_c(0.66, 105_000, 500)
    c_100k = calibrated_c(7.5, 1_050_000, 500)
    assert 1.0e-8 < c_10k < 2.0e-8
    assert 1.0e-8 < c_100k < 2.0e-8
    assert c_100k == pytest.approx(1.428e-8, rel=1e-2)


def test_worker_throughput() -> None:
    slots = worker_slots(2, 8)
    assert slots == 16
    assert theoretical_jobs_per_second(slots, 56.0) == pytest.approx(16 / 56.0)


def test_capacity_report_has_measured_coefficient() -> None:
    report = (ROOT / "docs" / "capacity-report.md").read_text(encoding="utf-8")
    assert "c ≈ 1.5e-8" in report
    assert "single_replica = c × nnz(H) × n_steps" in report
    assert "ScenarioA" in report and "ScenarioB" in report and "ScenarioC" in report
    assert "P95 < 500ms" in report
    assert "1.26e-8" in report and "1.43e-8" in report


def test_locustfile_defines_three_scenarios() -> None:
    text = (ROOT / "benchmarks" / "locustfile.py").read_text(encoding="utf-8")
    for name in ("ScenarioAReadHeavy", "ScenarioBBatchBurst", "ScenarioCAbuse"):
        assert f"class {name}" in text
    assert "/api/v1/auth/login" in text
    assert "/api/v1/runs" in text
    assert "X-Idempotency-Key" in text
    assert "429" in text
