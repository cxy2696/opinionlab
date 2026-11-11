# 使用场景与案例 / Use cases

OpinionLab 不局限于“舆情”两个字。任何**一群人互相影响、观点会变**的场景，都可以用同一套模型做情景推演：把人群抽象成节点，把“一起讨论/互相看见”的场合抽象成超边，把态度变化抽象成一次采纳，把反应快慢抽象成时延。

OpinionLab is not limited to public opinion. Any setting where **people influence each other and opinions change** can use the same model: people become nodes, group conversations become hyperedges, attitude shifts become adoption events, and reaction speed becomes latency.

> 它输出的是群体层面的“如果……可能会怎样”，不是对具体个人或真实事件的预测。
> It outputs group-level “what if” ranges, not predictions about individuals or real events.

## 案例 1：谣言来了，什么时候辟谣？ / When should we debunk a rumor?

- **场景**：一条谣言在社群里扩散，团队只能选一个投放时点。
- **模板**：`s2_rumor_debunk_timing.yaml`（S2）
- **怎么跑**：
  ```bash
  uv run python examples/rumor_timing.py --repeats 8
  ```
- **看什么**：T+2 / T+12 / T+24 的最终正向占比与 95% CI。CI 重叠时，不要对外宣称“越早越好”；增加副本或换更贴近数据的时延分布再试。
- **产出**：一张对比表 + 可下载的单文件报告，适合放进沟通方案评审。

## 案例 2：社区议事会不会变成沉默的多数？ / Does a community discussion converge or go silent?

- **场景**：业主群/议事会讨论一个争议议题，组织者想知道“轻推一把”是否有助于形成共识。
- **模板**：S7（社区议事共识）
- **怎么跑**：
  ```bash
  uv run python examples/community_consensus.py --repeats 6
  ```
- **看什么**：多样性没有塌到 0、收敛步变短，说明讨论在收敛而不是被压制；若多样性迅速归零，需要检查是不是“从众强度 `q` 太高”。
- **调整**：在演示页把 `q` 从 1.0 拉到 2.4，观察曲线拐点。

## 案例 3：组织变革沟通节奏 / Communication cadence during organizational change

- **场景**：公司分阶段宣布组织调整，担心员工情绪反弹。
- **模板**：S8（组织变革沟通）
- **怎么跑**：在浏览器演示中选择 S8，或用 CLI：
  ```bash
  uv run hnle simulate --spec scenarios/s8_organizational_change.yaml --repeats 20
  ```
- **看什么**：级联 P99 是否下降、多样性是否保持中等；如果两者同时恶化，说明沟通窗口需要拉长或换渠道。

## 案例 4：新品发布的口碑扩散 / Word of mouth at product launch

- **场景**：新品发布，创作者和真实用户混在一起，团队想知道“早期声量”是否等于“长期口碑”。
- **模板**：S9（新品发布口碑）
- **怎么跑**：选择 S9，调整 `q` 与平均时延，比较两次运行。
- **看什么**：早期级联大不代表后期多样性健康；重点看最终负向占比与多样性，而不是只看峰值。

## 案例 5：政策/平台治理的沟通窗口 / Policy and platform governance

- **场景**：政策分阶段发布，或平台对极端叙事做降温。
- **模板**：S1（政策发布节奏）、S3（平台治理）、S4（品牌 KOL）
- **看什么**：干预后的级联分布、收敛步与多样性；用“对比上一次”确认差异是否超过 CI 噪声。

## 案例 6：教学与研究复现 / Teaching and research reproduction

- **场景**：课堂上演示“从众强度”如何改变共识速度；或复现论文中的经典 Voter 极限。
- **模板**：G1（学术复现）
- **怎么跑**：`uv run hnle simulate --spec scenarios/g1_academic_reproduction.yaml --repeats 20`
- **看什么**：`q=1` 时共识概率随人群规模的变化趋势，以及不同随机种子下的分布。

## 把模型用到你自己的场景 / Adapting it to your own setting

1. 确定“人/账号/部门”是什么，以及他们为什么会被放在同一个超边里（同一话题、同一群、同一会议）。
2. 估计三件事：从众强度 `q`、平均反应时延与离散度、初始态度分布。
3. 用 `ModelSpec` 写一个 YAML（可参考 `scenarios/`），跑 `hnle simulate`；先看 95% CI，再谈结论。
4. 报告里保留假设、局限与免责声明——这三样和结果同样重要。

1. Decide what a node is and why nodes share a hyperedge (same topic, group or meeting).
2. Estimate conformity `q`, mean latency and dispersion, and the initial stance distribution.
3. Write a `ModelSpec` YAML (copy one from `scenarios/`) and run `hnle simulate`; read the 95% CIs before drawing conclusions.
4. Keep assumptions, limitations and the disclaimer with the report — they matter as much as the numbers.
