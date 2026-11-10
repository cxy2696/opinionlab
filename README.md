# OpinionLab · 舆情演化仿真沙盘

[中文](#中文) · [English](#english)

把 [HNL Voter Model](https://github.com/cxy2696/Hypergraph-Nonlinear-Latency-Voter-Model) 论文原型升级为**可复现、高性能、带蒙特卡洛置信区间与合规护栏**的舆论演化仿真平台 V1。

---

## 中文

### 项目状态

V1 已完成（26/26 user stories）。进度见 [`prd/agents/progress.txt`](prd/agents/progress.txt)，任务清单见 [`prd/agents/opinionlab-prd.json`](prd/agents/opinionlab-prd.json)。

设计文档：[架构](docs/ARCHITECTURE.md) · [数学模型](docs/MATH_MODEL.md) · [模型卡](docs/MODEL_CARD.md) · [合规](docs/COMPLIANCE.md) · [运维手册](docs/RUNBOOK.md) · [容量报告](docs/capacity-report.md) · [上线清单](docs/LAUNCH_CHECKLIST.md) · [CHANGELOG](CHANGELOG.md)

### 这是什么

- **引擎 `hnle`**：纯计算库，只依赖 numpy / scipy / pandas / pydantic，可 `pip install`、可离线 CLI 运行；超图 + 非线性采纳(q) + 异质时延。
- **服务层**：FastAPI + Postgres + Celery + Redis，负责排队、存储、鉴权、出图；引擎与平台解耦，论文复现不被平台绑架。
- **合规**：中国（个保法/等保二级）与欧盟（GDPR）双区一套代码，`DEPLOYMENT_MODE` 切换；只输出群体统计量，禁止单节点轨迹。

### 文档

| 文件 | 说明 |
|---|---|
| [`prd/舆情演化仿真沙盘PRD-v1.md`](prd/舆情演化仿真沙盘PRD-v1.md) | 唯一真相源：目标、缺陷审计（OPT-01…）、架构、数据模型、API、合规、部署 |
| [`prd/agents/opinionlab-prd.json`](prd/agents/opinionlab-prd.json) | 机器可读 user story 清单（26 条，含验收标准与完成状态） |
| [`prd/agents/progress.txt`](prd/agents/progress.txt) | 执行进度、代码库约定与每轮学习记录 |
| [`AGENTS.md`](AGENTS.md) / [`AGENTS.en.md`](AGENTS.en.md) | Agent 入口规范（中 / 英） |

### V1 目标

| # | 目标 | 量化验收 |
|---|---|---|
| G1 | 结果可复现 | 同 `run_manifest` 两次运行，指标数组逐位一致（1e-12） |
| G2 | 顺序无关 | 置换 `hyperedges` 顺序后同 seed 指标不变 |
| G3 | 性能 | 10 万节点 / 30 万超边 / 500 步，8 核 ≤ 90s；较上游 ≥ 50× 加速 |
| G4 | 统计可信 | 每个指标输出均值 + 95% CI（≥30 次独立副本） |
| G5 | 数据可用 | 5 类真实数据结构，ID 假名化后入库 |
| G6 | 场景可推演 | 6 个场景模板 + what-if 干预与 A/B 对比 |
| G7 | 双区合规 | 中国大陆 + 欧盟，一套代码 |

### 快速开始

```bash
make setup   # uv sync + 可选 docker compose（db/redis/minio）
make check   # ruff + mypy --strict + pytest
hnle version
```

### 开发方式（Ralph 循环）

每轮：读 JSON → 取 `priority` 最小且 `passes=false` 的 story → 实现 → `make check` → commit `feat: [US-xxx] [title]` → 置 `passes=true` → 追加进度。全部完成输出 `<promise>COMPLETE</promise>`。

### 硬性约束（摘自 PRD）

- 禁止引入 PRD 第 22 章未列出的依赖，禁止升级 major 版本
- 引擎核心禁止全局 `np.random.*` / `random.*`，随机性只能来自传入的 `numpy.random.Generator`
- 禁止任何接口返回单个节点的立场轨迹，只允许群体分位数（`NODE_TRACE_FORBIDDEN`）
- 禁止删除或改写 `tests/golden/` 基线数值而不说明原因
- 引擎与 worker 禁止 `plt.show()`，一律 matplotlib Agg + 文件输出
- 引擎零外部服务依赖：只依赖 numpy / scipy / pandas / pydantic，可离线运行

### 目录结构

```
packages/hnle/   # 引擎 + CLI（可独立安装）
apps/{api,worker,web}/
tests/           # 单测、黄金基线、置换不变、API 集成
benchmarks/      # 10 万节点基准
scenarios/       # 中/全球场景模板
migrations/      # alembic
docs/            # 架构、数学模型、合规、模型卡、运维手册
prd/             # PRD、任务清单、进度日志
```

### License

MIT，与上游论文原型一致。

---

## English

### What this is

OpinionLab upgrades the HNL Voter Model research prototype into a **reproducible, high-performance opinion-dynamics sandbox** with Monte-Carlo confidence intervals and compliance guardrails.

- **`hnle` engine**: a pure-computation library (numpy / scipy / pandas / pydantic only) with hypergraph interactions, non-linear adoption `q`, and heterogeneous latency. Installable and runnable offline via CLI.
- **Service layer**: FastAPI + Postgres + Celery + Redis for queueing, storage, auth, and reporting. The engine stays decoupled from the platform so paper reproduction never depends on the service stack.
- **Compliance**: one codebase for mainland China (PIPL / MLPS level 2) and the EU (GDPR), switched by `DEPLOYMENT_MODE`. Group-level statistics only — per-node trajectories are forbidden by design.

### Status

V1 is complete (26/26 stories). See [`prd/agents/progress.txt`](prd/agents/progress.txt) for the log and [`prd/agents/opinionlab-prd.json`](prd/agents/opinionlab-prd.json) for the backlog. Docs: architecture, math model, model card, compliance, runbook, capacity, launch checklist and changelog (links in the Chinese section).

### Documents

| File | Purpose |
|---|---|
| [`prd/舆情演化仿真沙盘PRD-v1.md`](prd/舆情演化仿真沙盘PRD-v1.md) | Single source of truth (Chinese): goals, defect audit, architecture, data model, API, compliance, deployment |
| [`prd/agents/opinionlab-prd.json`](prd/agents/opinionlab-prd.json) | Machine-readable 26-story backlog with acceptance criteria and pass state |
| [`prd/agents/progress.txt`](prd/agents/progress.txt) | Execution log, conventions, per-round learnings |
| [`AGENTS.md`](AGENTS.md) / [`AGENTS.en.md`](AGENTS.en.md) | Agent entry rules (Chinese / English) |

### V1 goals

| # | Goal | Quantified acceptance |
|---|---|---|
| G1 | Reproducible | Same `run_manifest` twice → metrics identical (1e-12) |
| G2 | Order-independent | Permuting `hyperedges` leaves metrics unchanged for the same seed |
| G3 | Fast | 100k nodes / 300k hyperedges / 500 steps in ≤ 90s on 8 cores; ≥ 50× upstream |
| G4 | Statistically sound | Every metric reports mean + 95% CI (≥ 30 replicas) |
| G5 | Usable data | Five real-world structures, IDs pseudonymised at ingest |
| G6 | Scenario sandbox | Six templates plus what-if interventions and A/B comparison |
| G7 | Dual-region compliance | China + EU on one codebase |

### Quick start

```bash
make setup   # uv sync + optional docker compose (db/redis/minio)
make check   # ruff + mypy --strict + pytest
hnle version
```

### Development loop (Ralph)

Each round: read the JSON → pick the lowest `priority` story with `passes=false` → implement → `make check` → commit `feat: [US-xxx] [title]` → set `passes=true` → append the progress log. Emit `<promise>COMPLETE</promise>` once every story passes.

### Hard constraints (from the PRD)

- No dependency outside PRD chapter 22; no major-version upgrades
- Engine core must not use global `np.random.*` / `random.*`; randomness comes from an injected `numpy.random.Generator`
- No endpoint may return a single node's opinion trajectory; group quantiles only (`NODE_TRACE_FORBIDDEN`)
- Never rewrite `tests/golden/` baselines without an explicit explanation
- No `plt.show()` in engine or worker; matplotlib Agg plus file output only
- The engine has zero external service dependencies and runs offline

### License

MIT, same as the upstream paper prototype.
