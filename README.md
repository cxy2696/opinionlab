# OpinionLab · 舆情演化仿真沙盘

[![CI](https://github.com/cxy2696/opinionlab/actions/workflows/ci.yml/badge.svg)](https://github.com/cxy2696/opinionlab/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](pyproject.toml)

[中文](#中文) · [English](#english)

**把“一群人会怎么想”变成可以反复试验、能看到误差范围的沙盘。**
A sandbox for exploring how opinions spread through groups — reproducible, with uncertainty ranges instead of single numbers.

**在线试用 / Live demo:** https://cxy2696.github.io/opinionlab/

![OpinionLab demo](docs/demo.png)

---

## 中文

### 它想解决什么问题

一条消息发出去，有人立刻转发，有人过两天才反应；小群体会互相强化，大群体会把少数声音盖过去。现实中的沟通、公关、社区治理和政策发布，常常只能“发完再看”。

OpinionLab 让你在发之前，先在沙盘里试：如果从众更强一点、如果反应更慢一点、如果早两天辟谣，群体的观点分布会怎么走？结果不是一个绝对数字，而是**一组带 95% 置信区间的可能范围**。

### 你可以用它做什么

- **危机沟通**：比较不同辟谣时点、不同降温力度下的负向占比与级联规模。
- **社区议事**：判断讨论是在形成共识，还是被从众压力压成“沉默的多数”。
- **组织变革**：试不同沟通节奏，观察员工情绪的反弹与回落。
- **新品发布**：区分“早期声量”与“长期口碑”，避免只看峰值。
- **教学与研究**：演示从众强度 `q` 如何改变共识速度；复现经典 Voter 模型极限。

每个场景在 [`docs/USE_CASES.md`](docs/USE_CASES.md) 里都有具体问题、命令和“该看什么”。

### 5 分钟上手

**在线试用**（无需安装）：打开 https://cxy2696.github.io/opinionlab/

界面采用 3D 工业追踪风格：旋转的舆情网络、目标锁定框、遥测与扫描线；右上角可一键切换中/英。每个参数都有“是什么/为什么调”的说明、悬停提示和一键预置（快速看 / 稳健估计 / 高从众 / 慢反应），不用先读文档。

**本地运行**（完整服务）：

```bash
git clone https://github.com/cxy2696/opinionlab.git
cd opinionlab
make demo        # 打开 http://127.0.0.1:8000
```

选一个模板，拖动 `q`，点“运行推演”。页面会显示多样性曲线、带 95% CI 的指标卡片；可以“对比上一次”，也可以下载单文件离线报告。

**命令行里跑**：

```bash
make setup
uv run hnle simulate --spec scenarios/s2_rumor_debunk_timing.yaml --repeats 20
uv run hnle report --run-id <run_id> --runs-dir runs
```

### 三个具体案例

1. **辟谣时点有没有用？**
   ```bash
   uv run python examples/rumor_timing.py --repeats 8
   ```
   对比 T+2 / T+12 / T+24 的最终正向占比。如果三组 CI 重叠，就不要对外说“越早越好”——在这组假设和样本量下，证据不足。

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

更多案例见 [`docs/USE_CASES.md`](docs/USE_CASES.md)。

### 它是怎么工作的

- **超图**：把“同一话题/同一群/同一场会议”里的人放在一条超边上，允许群体影响，而不只是两两对话。
- **两个旋钮**：从众强度 `q`（多容易跟随多数）和异质时延（每个人多久反应一次）。
- **可复现**：同一份配置 + 同一个种子，跑多少次结果都一样；每次运行都记录配置哈希、数据哈希和版本。
- **不确定性与护栏**：默认输出 95% CI；报告强制带免责声明；任何接口都不返回单个人的观点轨迹。

### 它不是什么

- 不是对真实舆情或个人立场的预测，也不做个体画像。
- 不模拟平台推荐算法、媒体议程和线下行为；这些需要另外的数据与模型。
- 参数估计得越粗，结论越只能当“方向性参考”。报告里会始终保留假设与局限。

### 模板库（15 个）

| 类别 | 模板 |
|---|---|
| 公共沟通 S1–S6 | 政策发布、辟谣时机、平台治理、品牌 KOL、应急科普、金融预期 |
| 通用场景 S7–S9 | 社区议事、组织变革、新品发布 |
| 研究与核查 G1–G7 | 学术复现、事实核查、公共卫生、平台系统性风险、灾害预警、企业变更；G5 选举类默认关闭，需用途审批 |

全部模板中英双语、可直接运行；`uv run hnle templates` 可列出。

### 常用命令

```bash
make demo    # 浏览器演示
make check   # ruff + mypy --strict + pytest
make bench   # 10 万节点基准（>90s 失败）
make migrate # 数据库迁移
```

### 文档

| 文档 | 内容 |
|---|---|
| [使用场景](docs/USE_CASES.md) | 6 类真实问题、命令与解读 |
| [产品演示](docs/DEMO.md) | 演示页、公开 API、限制 |
| [架构](docs/ARCHITECTURE.md) | 分层、数据流、模块地图 |
| [数学模型](docs/MATH_MODEL.md) | 公式与代码对应、采样 vs argmax |
| [模型卡](docs/MODEL_CARD.md) | 能力、局限、禁止用途 |
| [合规说明](docs/COMPLIANCE.md) | 双区、用途审批、删除与留存 |
| [运维手册](docs/RUNBOOK.md) | 指标、日志、回滚、tainted |
| [容量报告](docs/capacity-report.md) | 容量公式、实测系数、压测 |
| [CHANGELOG](CHANGELOG.md) | 行为变更与已知偏差 |

### 部署

- 单机：`docker-compose.yml`（db / redis / minio / api / worker）
- 集群：`deploy/k8s/helm-cn` 与 `helm-global` 两套 values
- 私有化：`deploy/private/OFFLINE.md`，无公网依赖

### License

MIT

---

## English

**Turn “how would this group react?” into something you can test repeatedly.**
OpinionLab turns a group-opinion question into a reproducible experiment with uncertainty ranges, not a single forecast.

**在线试用 / Live demo:** https://cxy2696.github.io/opinionlab/

![OpinionLab demo](docs/demo.png)

### What it is for

People influence each other in groups. A message spreads, a community argues, a company announces a change, a product launches. OpinionLab lets you try a scenario before you act: change conformity, latency or timing, then see how the distribution of opinions evolves — with 95% confidence intervals.

### What you can do

- **Crisis communication**: compare debunk timing and damping strength.
- **Community discussion**: tell consensus from conformity pressure.
- **Organizational change**: test communication cadence and sentiment rebound.
- **Product launch**: separate early buzz from durable word of mouth.
- **Teaching and research**: demonstrate how conformity `q` changes consensus; reproduce the classical voter limit.

Concrete questions, commands and reading guides live in [`docs/USE_CASES.md`](docs/USE_CASES.md).

### Live demo

Try it in the browser (no install): https://cxy2696.github.io/opinionlab/

### Quick start

```bash
git clone https://github.com/cxy2696/opinionlab.git
cd opinionlab
make demo        # http://127.0.0.1:8000

make setup
uv run hnle simulate --spec scenarios/s2_rumor_debunk_timing.yaml --repeats 20
uv run python examples/rumor_timing.py --repeats 8
uv run python examples/community_consensus.py --repeats 6
```

### How it works

- **Hypergraphs** model group influence, not only pairwise chats.
- **Two knobs**: conformity `q` and heterogeneous latency.
- **Reproducible**: same spec + seed gives the same result; every run records config/data hashes and versions.
- **Guardrails**: 95% CIs by default, a mandatory disclaimer in reports, and no per-person opinion traces.

### What it is not

- Not a prediction about real individuals or events, and not a profiling tool.
- It does not model platform recommender systems, media agenda or offline behaviour.
- Coarse parameters mean directional insight only; assumptions and limitations stay in the report.

### Templates (15)

S1–S6 for public communication (policy, debunking, governance, KOL, health, finance), S7–S9 for general use (community, organizational change, product launch), G1–G7 for research and verification (academic reproduction, fact-checking, public health, platform risk, disaster warning, corporate change). G5 election templates are disabled by default and require use-case approval.

### Docs

Architecture, math model, model card, compliance, runbook, capacity report, demo and use cases live under [`docs/`](docs), with links in the Chinese section.

### Deployment

Compose for a single host, Helm values for CN/global clusters, and an air-gapped delivery guide under [`deploy/`](deploy).

### License

MIT
