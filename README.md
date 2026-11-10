# OpinionLab（舆情演化仿真沙盘）

把 [HNL Voter Model](https://github.com/cxy2696/Hypergraph-Nonlinear-Latency-Voter-Model) 论文原型升级为**可复现、高性能、带蒙特卡洛置信区间与合规护栏**的舆论演化仿真平台 V1。

- 引擎包名：`hnle`
- 项目代号：OPINIONLAB
- 当前阶段：规划完成，等待按 user story 顺序实现
- 上游基线：`cxy2696/Hypergraph-Nonlinear-Latency-Voter-Model`（`model.py` / `random_simulation.py` / `real_world_simulation.py` / `sentimentdataset.csv`）

> 本仓库当前只包含规划文档（PRD + 机器可读任务清单 + 执行进度日志），代码将按任务清单逐条实现。

## 文档

| 文件 | 说明 |
|---|---|
| [`prd/舆情演化仿真沙盘PRD-v1.md`](prd/舆情演化仿真沙盘PRD-v1.md) | **唯一真相源**。目标、上游缺陷审计（OPT-01…）、架构、数据模型、API、合规、部署、目录结构、依赖版本 |
| [`prd/agents/opinionlab-prd.json`](prd/agents/opinionlab-prd.json) | 机器可读 user story 清单（含 acceptanceCriteria、priority、passes） |
| [`prd/agents/progress.txt`](prd/agents/progress.txt) | 执行进度与代码库约定（每轮追加学习记录） |

## V1 目标

| # | 目标 | 量化验收 |
|---|---|---|
| G1 | 结果可复现 | 同 `run_manifest` 两次运行，指标数组逐位一致（1e-12） |
| G2 | 顺序无关 | 置换 `hyperedges` 顺序后同 seed 指标不变 |
| G3 | 性能 | 10 万节点 / 30 万超边 / 500 步，8 核 ≤ 90s；较上游 ≥ 50× 加速 |
| G4 | 统计可信 | 每个指标输出均值 + 95% CI（≥30 次独立副本） |
| G5 | 数据可用 | 5 类真实数据结构，ID 假名化后入库 |
| G6 | 场景可推演 | 6 个场景模板 + what-if 干预与 A/B 对比 |
| G7 | 双区合规 | 中国大陆（个保法/等保二级）+ 欧盟（GDPR/数据最小化）一套代码 |

## 开发方式（Ralph 循环）

每轮：读 JSON → 取 `priority` 最小且 `passes=false` 的 story → 实现 → `make check`（ruff + mypy --strict + pytest，含 golden 回归）→ commit `feat: [US-xxx] [title]` → 置 `passes=true` → 追加 `progress.txt` 学习记录。全部通过后输出 `<promise>COMPLETE</promise>`。

### 硬性约束（摘自 PRD）

- 禁止引入 PRD 第 22 章未列出的依赖，禁止升级 major 版本
- 引擎核心禁止全局 `np.random.*` / `random.*`，随机性只能来自传入的 `numpy.random.Generator`
- 禁止任何接口返回单个节点的立场轨迹，只允许群体分位数（`NODE_TRACE_FORBIDDEN`）
- 禁止删除或改写 `tests/golden/` 基线数值而不说明原因
- 引擎与 worker 禁止 `plt.show()`，一律 matplotlib Agg + 文件输出
- 引擎零外部服务依赖：只依赖 numpy / scipy / pandas / pydantic，可 `pip install`、可离线 CLI 运行

## License

MIT（与上游论文原型一致）
