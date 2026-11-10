# 容量报告 / Capacity report

## 结论 / Summary
- 读流量不是瓶颈：20 org / 200 席位下峰值读 ≈ 5 QPS，2 个 API 实例有 50× 余量。
- 真正的瓶颈是 CPU 作业：单副本成本 ≈ **c × nnz(H) × n_steps**。
- 实测标定系数 **c ≈ 1.5e-8 s / 非零元 / 步**（比 PRD 初始假设 3e-9 高约 5×，以实测为准）。
- 推荐起步：**2 × 8C16G worker + 1 × 4C8G API/DB**；集中触发靠配额/优先级/预估，不靠横向扩容。
- Read traffic is not the bottleneck (~5 QPS peak); CPU simulation is.
- Measured **c ≈ 1.5e-8 s per non-zero per step**, ~5× the initial 3e-9 assumption.

## 公式 / Formula
```
single_replica = c × nnz(H) × n_steps
job_wall_clock = single_replica × repeats / jobs
jobs_per_second = worker_slots / average_job_seconds
```

## 标定 / Calibration
| 基准 / Benchmark | 节点 | 超边 | nnz | steps | 实测墙钟 | c |
|---|---|---|---|---|---|---|
| 10k nodes | 10,000 | 30,000 | ~105,000 | 500 | 0.66 s | 1.26e-8 |
| 100k nodes | 100,000 | 300,000 | ~1,050,000 | 500 | 7.5 s | 1.43e-8 |
| 采用值 / adopted | — | — | — | — | — | **1.5e-8** |

`make bench` 复现：10k 档约 0.7s，100k 档 < 90s；`benchmarks/bench_engine.py`。

## 作业示例 / Job examples (c=1.5e-8)
| nnz | steps | repeats | jobs | 单作业墙钟 |
|---|---|---|---|---|
| 1.2e6 | 500 | 50 | 8 | ≈ 56 s |
| 6e6 | 2000 | 100 | 8 | ≈ 2,250 s |
| 1.05e6 | 500 | 10 | 8 | ≈ 9.8 s |

## 压测场景 / Load scenarios
`benchmarks/locustfile.py`：

| 场景 | 配置 | 通过标准 |
|---|---|---|
| A 读为主 | 50 用户，3 job/s，15 min | API P95 < 500ms；队列积压不单调增长 |
| B 批量突发 | 20 用户，30 min 内约 60 个大作业 | 排队位次/预估时长正确；低优队列不被饿死 |
| C 恶意刷 | 单 org 500 job/s | 429 限流、熔断生效、DB 连接池不耗尽 |

运行 / Run:
```bash
locust -f benchmarks/locustfile.py ScenarioAReadHeavy --host http://localhost:8000 \
  --users 50 --spawn-rate 5 --run-time 15m --headless
locust -f benchmarks/locustfile.py ScenarioBBatchBurst --host http://localhost:8000 \
  --users 20 --spawn-rate 2 --run-time 30m --headless
locust -f benchmarks/locustfile.py ScenarioCAbuse --host http://localhost:8000 \
  --users 10 --spawn-rate 10 --run-time 5m --headless
```

## 观测 / Observability
- `opinionlab_api_duration_seconds` P95（A）
- `opinionlab_queue_depth`（B：不单调增长）
- `opinionlab_replica_failures_total` / 429 比例（C）
- `docs/RUNBOOK.md` 中的告警阈值即压测通过线。

## 假设与局限 / Assumptions & limitations
- 本报告 c 为单机 CSR 引擎实测，未含网络/DB 写回开销。
- 压测需真实 Postgres/Redis 与 worker；CI 只跑引擎基准，locust 场景在 staging 手工/定时执行。
- c 会随 numpy/BLAS/CPU 变化，发布前重跑 `make bench` 标定。
