"""Capacity model for simulation jobs (PRD 10.1).

    single replica ≈ c × nnz(H) × n_steps
    job wall clock ≈ single replica × repeats / jobs

``c`` is calibrated from the benchmark (see docs/capacity-report.md).
"""

from __future__ import annotations

DEFAULT_C = 1.5e-8  # seconds per non-zero per step, measured on the CSR engine


def single_replica_seconds(
    nnz: float, n_steps: int, c: float = DEFAULT_C
) -> float:
    return c * nnz * n_steps


def job_seconds(
    nnz: float,
    n_steps: int,
    repeats: int,
    jobs: int = 8,
    c: float = DEFAULT_C,
) -> float:
    if jobs < 1:
        raise ValueError("jobs must be >= 1")
    return single_replica_seconds(nnz, n_steps, c) * repeats / jobs


def calibrated_c(measured_seconds: float, nnz: float, n_steps: int) -> float:
    if nnz <= 0 or n_steps <= 0:
        raise ValueError("nnz and n_steps must be positive")
    return measured_seconds / (nnz * n_steps)


def worker_slots(workers: int, cores_per_worker: int = 8) -> int:
    return workers * cores_per_worker


def theoretical_jobs_per_second(slots: int, average_job_seconds: float) -> float:
    if average_job_seconds <= 0:
        raise ValueError("average_job_seconds must be positive")
    return slots / average_job_seconds
