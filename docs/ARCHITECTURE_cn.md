# 架构 / Architecture

> **一分钟版本**
>
> - 引擎（`packages/hnle`）不依赖数据库，可以单独跑；API 只负责多租户、作业与合规。
> - 报告与 API 只输出群体指标；单节点轨迹在边界被拒绝。
> - 本地先跑 `make demo`，再看 `apps/api` 与 `deploy/`。

## 分层 / Layers
```
┌──────────────────────────────────────────────┐
│ hnle 引擎（纯计算，可离线 pip 安装）          │
│ spec → graph → core(update/sparse/event)     │
│ → metrics → mc → sweep/calibrate → io/cli    │
└───────────────▲──────────────────────────────┘
                │
┌───────────────┴──────────────┐   ┌──────────────────┐
│ FastAPI 服务层（apps/api）    │   │ Celery worker     │
│ auth/RBAC/org 隔离/配额/审计  │   │ q_normal/q_batch  │
└───────┬──────────┬───────────┘   │ q_ingest          │
        │          │               └────────┬─────────┘
   PostgreSQL     Redis                    MinIO/S3
   (RLS/分区)     (队列/进度/限流)          (产物)
```

- 引擎与服务解耦：`packages/hnle` 只依赖 numpy/scipy/pandas/pydantic/typer，可离线 CLI 复现论文结论。
- 服务层负责排队、鉴权、存储、出图；`runs` 一旦产出只读，改参数即新 run。
- 引擎与服务层 / Engine and service layer are decoupled; the engine has zero external service dependencies.

## 数据流 / Data flow
1. `ingest_csv`：UTF-8 → 假名化（HMAC）→ hashtag 清洗 → 情绪映射 → 确定性节点序 → `Hypergraph` + 权重。
2. `simulate`：`ModelSpec` → `run_sparse`/`run_event`（注入 Generator）→ `RunResult`（群体序列）。
3. `run_monte_carlo`：`SeedSequence.spawn` 派生副本 → Welford 聚合 + 95% CI。
4. `export_run`：manifest（sha/版本/耗时）→ series.csv / metrics.parquet / 单文件 HTML（内嵌 ECharts）/ graph.npz。
5. 服务层：`runs.aggregate` 存聚合指标；产物引用对象存储；审计只追加。

## 模块地图 / Module map
| 模块 | 职责 |
|---|---|
| `hnle/spec.py` | 唯一参数真相源 `ModelSpec` |
| `hnle/graph.py` | 超图、确定性排序、权重归一 |
| `hnle/ingest.py` | CSV 接入、清洗、假名化、PII 拒绝 |
| `hnle/core/update.py` | 节点中心参考实现（OPT-01） |
| `hnle/core/sparse.py` | CSR 向量化引擎（OPT-20） |
| `hnle/core/event.py` | 事件驱动引擎（OPT-21） |
| `hnle/core/shocks.py` | 冲击 / 干预 / 拓扑演化 |
| `hnle/metrics.py` | 多样性、熵、极化、振荡、收敛 |
| `hnle/mc.py` | 并行副本与置信区间 |
| `hnle/sweep.py` / `calibrate.py` | 扫参、敏感性、校准 |
| `hnle/io/*` | manifest、导出、报告、场景加载 |
| `apps/api/app/*` | FastAPI、RBAC、配额、审计、观测 |

## 关键不变量 / Invariants
- 所有参数只经 `ModelSpec`；CLI/API 不允许私有参数名。
- 引擎内无全局 RNG；随机性只来自传入的 `Generator`（`SeedSequence.spawn` 分流）。
- 超边顺序规范化后再计算，保证置换不变（G2）。
- 只输出群体统计量；单节点轨迹接口固定 `NODE_TRACE_FORBIDDEN`。
- 报告必须带固定免责声明，缺失即 `DISCLAIMER_MISSING`。
- No global RNG; only group-level statistics; reports fail without a disclaimer.

## 部署 / Deployment
- Compose：db / redis / minio / api / worker（见 `docker-compose.yml`）。
- 双区：`REGION=cn|global` + `deploy/k8s/helm-{cn,global}` 的域名/桶/密钥差异。
- 私有化：`deploy/private/OFFLINE.md` 全离线镜像 + wheel 交付。
