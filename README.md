# OpinionLab · 舆情演化仿真沙盘

[中文](#中文) · [English](#english)

OpinionLab 是一个**可复现、可服务化**的舆论动力学仿真平台：在超图上模拟群体观点演化，支持非线性从众、异质时延、外部冲击与干预推演，并输出带 95% 置信区间的群体指标与离线报告。

OpinionLab is a reproducible opinion-dynamics simulation platform. It models group opinion evolution on hypergraphs with non-linear conformity, heterogeneous latency, external shocks and intervention scenarios, and reports group-level metrics with 95% confidence intervals.

---

## 中文

### 特性

- **引擎 `hnle`**：纯计算库，只依赖 numpy / scipy / pandas / pydantic，可 `pip install`、可离线 CLI 运行
- **两种内核**：CSR 稀疏向量化（默认）与事件驱动（长时延更省算力）；`L≡1` 时结果逐位一致
- **可复现**：`ModelSpec` 单一参数源、`SeedSequence` 流拆分、manifest（config/data/git sha）、`hnle report` 逐位重建
- **统计**：多样性、熵、极化、级联分位、收敛/吸收态、振荡四件套；Welford 均值 + 95% CI
- **场景**：12 个中/全球模板（政策、辟谣、治理、KOL、科普、金融、学术复现等），支持 `--set` 覆盖
- **服务层**：FastAPI + Postgres + Celery + Redis；JWT/RBAC、租户隔离、配额、限流、审计、Prometheus
- **合规**：CN/EU 双区隔离、G5 用途审批、PII 拒收、单节点轨迹禁止、强制免责声明
- **报告**：单文件离线 HTML（内嵌 ECharts）、CI 图表、manifest、中英免责声明

### 产品演示 / Demo

```bash
make demo
# 打开 http://127.0.0.1:8000
```

浏览器中即可选择场景、调整从众强度/时延/副本数，查看带 95% CI 的指标与多样性曲线，并下载单文件离线报告。详见 [演示说明](docs/DEMO.md)。

![OpinionLab demo](docs/demo.png)

A no-login browser demo is included: pick a scenario, tune parameters, inspect metrics with confidence intervals and download an offline report. See [docs/DEMO.md](docs/DEMO.md).

### 快速开始

```bash
make setup          # uv sync（可选 docker compose 启动 db/redis/minio）
make check          # ruff + mypy --strict + pytest
make bench          # 10 万节点基准（>90s 失败）

hnle simulate --spec scenarios/s2_rumor_debon_timing.yaml --repeats 50
hnle templates
hnle report --run-id <run_id> --runs-dir runs
```

需要 Postgres/Redis 的集成测试通过 `TEST_DATABASE_URL` 启用；本地可用 Docker Compose：

```bash
docker compose up -d db redis minio
export DATABASE_URL=postgresql+asyncpg://app:CHANGE_ME@localhost:5432/opinionlab
export TEST_DATABASE_URL=$DATABASE_URL
uv run alembic upgrade head
make check
```

### 文档

| 文档 | 内容 |
|---|---|
| [架构](docs/ARCHITECTURE.md) | 分层、数据流、模块地图、不变量 |
| [数学模型](docs/MATH_MODEL.md) | 公式与代码对应、sampling vs argmax、数值可复现 |
| [模型卡](docs/MODEL_CARD.md) | 能力、局限、禁止用途、数据与合规 |
| [合规说明](docs/COMPLIANCE.md) | 双区、用途审批、删除与留存 |
| [运维手册](docs/RUNBOOK.md) | 指标/告警、日志、金丝雀、回滚、tainted |
| [容量报告](docs/capacity-report.md) | 容量公式、实测 c、压测场景 |
| [产品演示](docs/DEMO.md) | 演示页、公开 API、限制与适用场景 |
| [CHANGELOG](CHANGELOG.md) | 行为变更、依赖与已知偏差 |

### 目录

```
packages/hnle/   # 引擎 + CLI
apps/api/        # FastAPI 服务层
apps/worker/     # Celery worker 入口
tests/           # 单测、金标、集成测试
benchmarks/      # 性能基准与 locust 场景
scenarios/       # 场景模板与情绪映射
migrations/      # Alembic 迁移
deploy/          # Compose、K8s values、离线交付
docs/            # 设计、模型卡、合规、运维
```

### 部署

- 单机：`docker-compose.yml`（db / redis / minio / api / worker）
- 集群：`deploy/k8s/helm-cn` 与 `helm-global` 两套 values
- 私有化：`deploy/private/OFFLINE.md`，无公网依赖

### License

MIT

---

## English

### Features

- **`hnle` engine**: pure computation, depends only on numpy / scipy / pandas / pydantic; installable and runnable offline
- **Two kernels**: CSR sparse (default) and event-driven (cheaper for long latencies); bit-identical at `L≡1`
- **Reproducible**: single `ModelSpec`, `SeedSequence` stream splitting, manifest with config/data/git hashes, `hnle report` rebuilds curves exactly
- **Statistics**: diversity, entropy, polarisation, cascade quantiles, convergence/absorption, oscillation measures; Welford mean + 95% CI
- **Scenarios**: 12 CN/global templates (policy, debunking, governance, KOL, health, finance, academic, …) with `--set` overrides
- **Service layer**: FastAPI + Postgres + Celery + Redis; JWT/RBAC, tenant isolation, quotas, rate limits, audit, Prometheus
- **Compliance**: CN/EU region isolation, G5 use-case approval, PII rejection, no node-level traces, mandatory disclaimer
- **Reports**: single-file offline HTML with an embedded ECharts bundle, CI charts, manifest, bilingual disclaimer

### Quick start

```bash
make setup          # uv sync (optional compose for db/redis/minio)
make check          # ruff + mypy --strict + pytest
make bench          # 100k-node benchmark (fails above 90s)

hnle simulate --spec scenarios/s2_rumor_debon_timing.yaml --repeats 50
hnle templates
hnle report --run-id <run_id> --runs-dir runs
```

Database-backed tests are enabled through `TEST_DATABASE_URL`. Use Docker Compose locally as shown above.

### Docs

Architecture, math model, model card, compliance, runbook, capacity report and changelog live under [`docs/`](docs) with links in the Chinese section.

### License

MIT
