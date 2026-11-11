# Capacity report

## Summary

- Read traffic is not the bottleneck: at 20 orgs / 200 seats, peak reads are about 5 QPS, leaving
  roughly 50× headroom on two API instances.
- CPU simulation is the bottleneck: one replica costs about `c × nnz(H) × n_steps`.
- Measured calibration is `c ≈ 1.5e-8 s per non-zero per step`, about 5× the early 3e-9 assumption.
- Starting point: 2 × 8C16G workers + 1 × 4C8G API/DB; absorb bursts with quotas, priority and
  estimates rather than horizontal scaling.

## Formula

```
single_replica = c × nnz(H) × n_steps
job_wall_clock = single_replica × repeats / jobs
jobs_per_second = worker_slots / average_job_seconds
```

## Calibration

| Benchmark | Nodes | Hyperedges | nnz | Steps | Wall clock | c |
|---|---|---|---|---|---|---|
| 10k nodes | 10,000 | 30,000 | ~105,000 | 500 | 0.66 s | 1.26e-8 |
| 100k nodes | 100,000 | 300,000 | ~1,050,000 | 500 | 7.5 s | 1.43e-8 |
| adopted | — | — | — | — | — | **1.5e-8** |

Reproduce with `make bench`: about 0.7 s for 10k and under 90 s for 100k
(`benchmarks/bench_engine.py`).

## Job examples (c = 1.5e-8)

| nnz | Steps | Repeats | Jobs | Wall clock |
|---|---|---|---|---|
| 1.2e6 | 500 | 50 | 8 | ≈ 56 s |
| 6e6 | 2000 | 100 | 8 | ≈ 2,250 s |
| 1.05e6 | 500 | 10 | 8 | ≈ 9.8 s |

## Load scenarios

`benchmarks/locustfile.py`:

| Scenario | Setup | Pass criteria |
|---|---|---|
| A read-heavy | 50 users, 3 job/s, 15 min | API P95 < 500 ms; queue does not grow monotonically |
| B batch burst | 20 users, ~60 large jobs in 30 min | queue position/ETA correct; low-priority not starved |
| C abuse | one org at 500 job/s | 429s and circuit breaker work; DB pool not exhausted |

```bash
locust -f benchmarks/locustfile.py ScenarioAReadHeavy --host http://localhost:8000 \
  --users 50 --spawn-rate 5 --run-time 15m --headless
locust -f benchmarks/locustfile.py ScenarioBBatchBurst --host http://localhost:8000 \
  --users 20 --spawn-rate 2 --run-time 30m --headless
locust -f benchmarks/locustfile.py ScenarioCAbuse --host http://localhost:8000 \
  --users 10 --spawn-rate 10 --run-time 5m --headless
```

## Observability

- `opinionlab_api_duration_seconds` P95 (A)
- `opinionlab_queue_depth` (B; must not grow monotonically)
- `opinionlab_replica_failures_total` / 429 ratio (C)
- Alert thresholds in `docs/RUNBOOK.md` are the pass lines.

## Assumptions and limitations

- `c` is measured on a single-host CSR engine; network and DB write-back are excluded.
- Load tests need real Postgres/Redis and workers; CI runs only the engine benchmark, while locust
  scenarios run manually or on a schedule in staging.
- `c` changes with numpy/BLAS/CPU; recalibrate with `make bench` before every release.
