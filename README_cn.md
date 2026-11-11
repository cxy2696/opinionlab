# OpinionLab · 舆情演化仿真沙盘

[![CI](https://github.com/cxy2696/opinionlab/actions/workflows/ci.yml/badge.svg)](https://github.com/cxy2696/opinionlab/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](pyproject.toml)

**中文** · [English](README_en.md) · [语言入口](README.md)

**把“一群人会怎么想”变成可以反复试验、能看到误差范围的沙盘。**
它不是算命，而是让你在发消息、开发布会、改政策之前，先试几种“如果……会怎样”。

**在线体验：** https://cxy2696.github.io/opinionlab/

![OpinionLab 演示](docs/demo.png)

![3D 观测阵列](docs/telemetry-3d.png)

*① 观点地形 ② 级联柱阵 ③ 立场粒子云*

## 它解决什么问题

一条消息发出去，有人立刻转发，有人过两天才反应；小群体会互相强化，大群体会把少数声音盖过去。
现实中的沟通、公关、社区治理和政策发布，常常只能“发完再看”。

OpinionLab 把这件事变成实验：改变从众强度、反应时延、干预时点，观察群体观点怎么走。
输出不是一个绝对数字，而是**一组带 95% 置信区间的可能范围**，以及“这个结果能支持什么判断”的说明。

## 你能用它做什么

| 场景 | 具体问题 | 模板 |
|---|---|---|
| 危机沟通 | 辟谣早两天/晚两天，负向占比差多少？ | S2 |
| 社区议事 | 讨论是在形成共识，还是被压成沉默多数？ | S7 |
| 组织变革 | 分阶段宣布，员工情绪何时反弹？ | S8 |
| 新品发布 | 早期声量等于长期口碑吗？ | S9 |
| 政策/平台治理 | 干预窗口放在哪，级联会怎么变？ | S1 / S3 |
| 教学与研究 | `q` 如何改变共识？经典 Voter 极限是什么？ | G1 |

每个场景的配置方法、命令和解读要点见 [`docs/USE_CASES_cn.md`](docs/USE_CASES_cn.md)。

## 60 秒上手

**在线版**（无需安装）：https://cxy2696.github.io/opinionlab/

**本地完整版：**

```bash
git clone https://github.com/cxy2696/opinionlab.git
cd opinionlab
make demo        # http://127.0.0.1:8000
```

选一个模板，拖动 `q`，点“运行推演”。页面会显示多样性曲线、带 95% CI 的指标、决策提示和 3D 观测阵列。

**命令行：**

```bash
make setup
uv run hnle simulate --spec scenarios/s2_rumor_debunk_timing.yaml --repeats 20
uv run hnle report --run-id <run_id> --runs-dir runs
```

## 界面里有什么

- **3D 工业追踪**：旋转的舆情网络、目标锁定框、扫描线、节点/步数/分歧遥测。
- **3D 观测阵列**：观点地形、级联柱阵、立场粒子云；带峰值/当前值、图例，柱阵可悬浮读数。
- **参数解释**：每个参数都有“是什么/为什么调”的说明、悬停提示和一键预置（快速看 / 稳健估计 / 高从众 / 慢反应）。
- **决策提示**：帮助判断什么、关键时点（起势/峰值/多数/干预）、建议窗口、后续验证清单。
- **中英切换**：右上角一键切换，模板、图表、总结、决策提示同步切换。
- **可选 Ollama 辅助解读**：默认关闭，只把结果翻译成人话并建议下一步推演，不计算指标、不替代结论。

## 三个具体案例

1. **辟谣时点有没有用？**
   ```bash
   uv run python examples/rumor_timing.py --repeats 8
   ```
   对比 T+2 / T+12 / T+24 的最终正向占比。如果 CI 重叠，就不要说“越早越好”——在这组假设和样本量下证据不足。

2. **社区讨论会不会被压成沉默？**
   ```bash
   uv run python examples/community_consensus.py --repeats 6
   ```
   把 `q` 从 1.0 调到 2.4。理想情况是收敛变快但多样性没有塌到 0；如果多样性迅速归零，说明讨论可能是被“压”下去的。

3. **学术复现**
   ```bash
   uv run hnle simulate --spec scenarios/g1_academic_reproduction.yaml --repeats 20
   ```
   在 `q=1`、二元超边、单位时延下，检查共识概率随人群规模的变化趋势。

更多见 [`docs/USE_CASES_cn.md`](docs/USE_CASES_cn.md)。

## 仓库地图

| 路径 | 一句话说明 |
|---|---|
| `packages/hnle/` | 可独立运行的仿真引擎：模型、超图、两种内核、指标、Monte Carlo、报告；不依赖数据库 |
| `apps/api/` | FastAPI 服务：登录/RBAC、配额、作业、连接器、合规、演示 API |
| `apps/web/` | 本地演示前端源码：HTML/CSS/JS、3D 场景、粒子、星系；数据来自 API |
| `site/` | GitHub Pages 站点：只保留站点专属文件，构建时从 `apps/web` 复制共享资源 |
| `scenarios/` | 15 个中英双语场景模板，直接可跑 |
| `examples/` | 两个最小可运行案例：辟谣时点、社区从众 |
| `tests/` | 单元、集成、金标与前端/文档测试 |
| `docs/` | 中英文成对的数学、架构、合规、运维、演示文档 |
| `benchmarks/` | 容量基准与 Locust 压测脚本 |
| `deploy/` | Compose、Helm（CN/Global）与离线交付 |
| `scripts/` | 静态站构建、场景模板导出 |
| `migrations/` | Alembic 数据库迁移 |

## 数学与可复现

模型定义、超边加权、`q` 的极限行为、时延语义、Monte Carlo 估计量与置信区间假设，都写在
[`docs/MATH_MODEL_cn.md`](docs/MATH_MODEL_cn.md)。每条公式都对应到具体代码函数，并明确列出
“哪些结论只能方向性使用”。先看结论可以读 [`docs/MODEL_CARD_cn.md`](docs/MODEL_CARD_cn.md)。

## 模板库（15 个）

- **S1–S6 公共沟通**：政策发布、辟谣时机、平台治理、品牌 KOL、应急科普、金融预期
- **S7–S9 通用场景**：社区议事、组织变革、新品发布
- **G1–G7 研究与核查**：学术复现、事实核查、公共卫生、平台系统性风险、灾害预警、企业变更；G5 选举类默认关闭，需用途审批

全部模板中英双语、可直接运行；`uv run hnle templates` 可列出。

## 文档

| 文档 | 内容 |
|---|---|
| [文档导航](docs/README_cn.md) | 按角色选阅读路径 |
| [使用场景](docs/USE_CASES_cn.md) | 6 类真实问题、命令与解读 |
| [产品演示](docs/DEMO_cn.md) | 演示页、公开 API、限制、Ollama |
| [架构](docs/ARCHITECTURE_cn.md) | 分层、数据流、模块地图 |
| [数学模型](docs/MATH_MODEL_cn.md) | 公式、`q` 极限、估计量与失效边界 |
| [模型卡](docs/MODEL_CARD_cn.md) | 能力、局限、禁止用途 |
| [合规说明](docs/COMPLIANCE_cn.md) | 双区、用途审批、删除与留存 |
| [运维手册](docs/RUNBOOK_cn.md) | 指标、日志、回滚、tainted |
| [容量报告](docs/capacity-report_cn.md) | 容量公式、实测系数、压测 |
| [变更日志](CHANGELOG_cn.md) | 行为变更与已知偏差 |

## 开发与测试

```bash
make check   # ruff + mypy --strict + pytest
make bench   # 10 万节点基准，>90s 失败
make site    # 组装 GitHub Pages 静态站
```

- 220+ 测试覆盖引擎、API、演示页、文档与金标基线。
- Postgres/Redis 集成测试使用 CI service；本地可用 `TEST_DATABASE_URL`。
- 前端共享资源只在 `apps/web/` 维护，Pages 构建时复制，避免双份代码。

## 部署

- 单机：`docker-compose.yml`（db / redis / minio / api / worker）
- 集群：`deploy/k8s/helm-cn` 与 `helm-global`
- 私有化：`deploy/private/OFFLINE_cn.md`，无公网依赖

## 边界

- 不做个人观点预测、画像或打分。
- 不模拟平台推荐算法、媒体议程、线下行为与真实价格反馈。
- 参数未标定时，结论只具方向性；报告始终保留假设、局限与免责声明。

## License

MIT
