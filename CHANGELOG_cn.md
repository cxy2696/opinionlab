# Changelog

> **一分钟版本**
>
> - v1.0 从论文原型升级：节点中心更新、显式决策规则、确定性 RNG、清单与 CI。
> - 行为变化会导致结果与上游原型不同，这是有意为之。
> - 已知偏差与容量系数会随环境变化，发布前重跑基准。

## v1.1.0 — 2026-11-12

### 数学与逻辑修正

- `threshold` 规则改为：只有当更可能的立场**严格优于**当前立场且其概率达到阈值时才切换；并列时保持现状。
  旧实现只看 `p1 >= τ`，忽略当前立场。
- `max` 聚合现在按行重新归一化。逐元素最大值不是概率分布；旧实现可能把行和大于 1 的向量交给采样器。
- 移除 `zscore` 权重归一化。它可能产生负权重，使加权计数为负、分数次幂 `q` 无定义。权重规范为非负；
  总权重为零的超边回退到均匀分布并给出警告。
- 事件引擎改用与 CSR 引擎相同的“改变立场后计时”规则，使用加权计数（旧实现只数节点数），并按每个整数步记录序列。
  事件引擎只支持整数时延；连续时延由 CSR 引擎处理。
- 从众映射、行归一化、序数平均立场与共识判定集中到共享的 `core/kernel.py`，三个引擎不再各自复制公式。
- `engagement` 与 `centrality` 权重来源现在真正生效：接入权重挂到 `Hypergraph` 并传入引擎；`centrality` 使用入射超边度数。
  旧实现中这两个来源会静默退回均匀权重。

### 行为变更（破坏性）

- 上述 threshold 语义变化：旧版在 `p1 >= τ` 时切到 1 的运行，现在可能保持当前立场。
- `weights.normalize = "zscore"` 在参数校验阶段被拒绝；请使用 `none` 或 `max`。
- `engine = "event_driven"` 与 `latency.quantize = "continuous"` 组合被拒绝；请使用 `engine = "sparse_vector"`。
- 重复超边会被合并，超边内重复节点编号会被拒绝。合成生成器现在采样**互不相同**的超边，因此 voter-limit 金标基线已更新。

### 测试与文档

- 新增 threshold 保持现状、max 归一化、整数时延下事件/CSR 在 `L = 2` 与 `L = 5` 的逐步一致、事件引擎加权计数、
  二元专用控制等测试。
- 重写 `docs/MATH_MODEL_en.md` / `_cn.md`：`q > 0`、非负权重、归一化 `max`、明确的 threshold 语义、
  整数事件时钟、Student-*t* 区间，以及 `time_to_consensus = -1` 的删失含义。
- 因互异超边生成器更新 `tests/golden/v1_baseline.json`；`pre_fix_baseline.json` 不变。

## v1.0.0 — 2026-11-11（从上游论文原型升级）
### 行为变更 / Behaviour changes
- **OPT-01 更新语义**：从"遍历超边就地覆盖 + 提前写 last_change_time"改为节点中心、步末原子写回；结果与超边顺序无关（`tests/test_permutation_invariance.py`）。理由：可复现性根因。
- **RNG 收口**：移除全局 `np.random.*`/`random.*`，统一 `SeedSequence.spawn` 三流（init/latency/decision）；golden 数值随流拆分更新。
- **data_driven 初始化**：修复真实数据入口用随机初始化覆盖情绪观点的缺陷；初始多数派比例与正向标签占比一致。
- **decision_rule**：新增 `stochastic|argmax|threshold`，显式标注论文公式(3)（argmax）与上游实现（stochastic）的差异。
- **多立场**：支持 `n_opinions=2..6`；ε 聚合与指标按 k 泛化。
- **时延**：离散引擎按最后改变时间判定；事件引擎按每次尝试重新调度，`L≡1` 时二者逐位一致。
- **指标重做**：移除"`np.mean(opinions)` 当振荡"的旧逻辑，改为 FFT 主频占比/过零率/自相关/符号持续度；新增熵、极化、活跃立场、assortativity、级联分位、收敛稳定性。
- **可复现工程**：manifest（config/data sha、git sha、版本、耗时）、run_id=config_sha[:16]-seed、graph.npz、`hnle report` 逐位重建。
- **报告护栏**：单文件离线 HTML（内嵌 ECharts）、强制免责声明、样本不足徽标、单副本水印。

### 依赖与基础设施 / Dependencies & infra
- 引擎依赖按版本表锁定；新增 `pyyaml==6.0.1`（YAML 加载验收要求）、`click==8.1.7`（typer 0.12.3 兼容）、dev `pandas-stubs`/`locust`/`pip-audit`。
- 服务层：FastAPI + SQLAlchemy async + Alembic；Postgres 分区 + RLS；Celery 三队列。
- 迁移 0001..0005：初始 schema、refresh/idempotency/shares、cancelling 状态、合规字段与用途审批、runs.tainted。

### 已知偏差 / Known deviations
- 分区表唯一键必须含 `created_at`；`(org_id, run_id_external)` 唯一约束包含它。
- `runs`/`run_replicas` 增加 `created_at`；`run_replicas`/`artifacts` 增加 `run_created_at` 以做复合外键。
- `TopologySpec` 增加 `arrival_rate`/`decay_rate`（原 spec 表只列 mode）。
- `edge_boost` 暂以概率偏置近似（引擎尚无超边权重）。
