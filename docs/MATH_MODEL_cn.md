# 数学模型 / Math model

> **一分钟版本**
>
> - `q` 控制跟随多数的强度：`q=1` 是线性 Voter，`q→∞` 趋向多数锁定。
> - 95% CI 是副本均值的正态近似；`R<30` 只应作方向性参考。
> - 这是情景推演，不是因果识别；参数未标定时不要下强结论。

这份文档把 OpinionLab 的更新规则写成可检查的数学对象，并逐条对应到代码。目标不是“看起来像论文”，
而是让每个数字都能回答三个问题：**它定义了什么、它依赖什么假设、它在什么情况下不可信。**

## 1. 符号与状态

- 超图 `H = (V, E)`：`V` 是节点（人/账号/部门），`e ∈ E` 是群体互动场景（话题、群聊、会议）。
- 节点权重 `α_j > 0`：默认按互动量归一化；均匀权重时 `α_j = 1`。
- 观点取值 `X_i ∈ {1, …, K}`；V1 默认 `K=2`，但引擎支持多立场。
- 时延 `L_i ≥ 0`：节点两次更新之间的最小间隔；`T_i` 是上次改变立场的时刻。
- 决策规则 `decision_rule ∈ {stochastic, argmax, threshold}`。

## 2. 超边上的加权分布

对超边 `e` 和立场 `x`：

```
S_x(e) = Σ_{j∈e} α_j · 1(X_j = x)
```

`S_x` 是**加权计数**，不是归一化比例；后续公式中分母会消去尺度。默认节点聚合使用
`mean`（即对入射超边取平均），也支持 `max` 与 `size_weighted`。

## 3. 非线性从众映射

二元情形：

```
p_1(e) = S_1(e)^q / (S_0(e)^q + S_1(e)^q)
p_0(e) = 1 - p_1(e)
```

多立场情形：

```
p_v(e) = S_v(e)^q / Σ_u S_u(e)^q
```

`q` 的极限行为（这是结论解释的依据）：

| 情形 | 行为 |
|---|---|
| `q → 0` | 所有非空立场的概率趋于均匀 `1/K`（完全忽略多数） |
| `q = 1` | 线性 Voter：概率正比于加权占比 |
| `q → ∞` | 概率质量集中到 `argmax_x S_x(e)`；并列时均分 |

实现：`core/update.py::edge_distributions`、`core/sparse.py::_node_probabilities`。

## 4. 节点聚合与更新

节点 `i` 的入射超边集合记为 `E_i`。对每条边得到一个概率向量 `p(e)`，聚合为：

```
p_i = A_{e∈E_i} p(e)
```

`A` 由 `aggregation` 决定（`mean` / `max` / `size_weighted`）。随后：

- **就绪条件**：`t - T_i ≥ L_i`；不满足的节点本步不更新。
- **随机规则**（默认）：`X_i(t+1) ~ Categorical(p_i)`，与上游动力学一致。
- **argmax 规则**（论文公式 (3) 的确定性版本）：`X_i(t+1) = argmax_v p_i(v)`。
- **threshold 规则**：仅当 `max_v p_i(v) ≥ τ` 时切换到该立场，否则保持。

离散引擎在步末原子写回；事件引擎按 `L_i` 重新调度。`L_i ≡ 1` 时两者逐步一致
（`tests/test_engine_equivalence.py`）。

## 5. Monte Carlo 估计与置信区间

同一 `ModelSpec` 下独立运行 `R` 个副本，得到指标 `Y_1, …, Y_R`（例如最终多样性）：

```
mean = (1/R) Σ_r Y_r
var  = (1/(R-1)) Σ_r (Y_r - mean)^2
CI95 ≈ mean ± 1.96 · sqrt(var / R)
```

实现：`hnle/mc.py`（Welford 在线更新，避免大样本数值漂移）。

**严谨性说明**：

- 该区间是**正态近似**；`R` 较小时只应作为方向性参考，`R < 30` 会给出 underpowered 警告。
- 同时报告多个指标时，不对“所有指标同时覆盖”作保证；不要挑一个显著的结果讲故事。
- 副本必须独立同分布；共享随机流会低估方差，引擎为每个副本用 `SeedSequence` 分流。
- 时间到共识等指标存在**删失**（未在窗口内达到多数）；报告需说明删失比例，不能把“未达到”当作 0。

## 6. 可复现与不变量

- 超边先排序再聚合，浮点求和顺序固定；置换节点顺序不改变结果（`atol=0` 可验证）。
- 每个副本的初始化、时延、决策使用独立的 `SeedSequence.spawn(3)` 流，避免流间耦合。
- 指标使用 float64；测试统一用 `numpy.testing.assert_allclose`，禁止 `==`。
- API 与报告只输出群体统计量，任何单节点轨迹在边界被拒绝。

## 7. 公式与代码对照

| 公式 | 代码 |
|---|---|
| `S_x(e) = Σ α_j 1(X_j=x)` | `core/update.py::edge_distributions`、`core/sparse.py::_node_probabilities` |
| `p_v(e) = S_v^q / Σ S_u^q` | 同上 |
| 就绪 `t - T_i ≥ L_i` | `core/update.py::run_simulation` |
| 聚合 `mean/max/size_weighted` | `aggregate_node_probabilities` |
| `diversity = 1 - max_v share_v` | `metrics.diversity` |
| `entropy = -Σ p ln p`（实现用 bit） | `metrics.shannon_entropy` |
| 振荡：FFT 主频占比 / 过零率 / lag-k 自相关 | `metrics.fft_power_ratio` 等 |
| 收敛、吸收态 | `metrics.time_to_consensus` / `consensus_stability` |
| 单副本成本 `c·nnz·steps` | `hnle/capacity.py`（实测 c≈1.5e-8） |

## 8. 假设与失效边界

- 拓扑与权重来自给定数据；模型不推断真实关系，也不建模推荐算法、媒体议程或线下行为。
- 参数 `q`、时延与初始分布必须外部标定；未标定时，结论只具方向性。
- 模型是**情景推演**，不是因果识别：改变参数后的差异不能直接解释为真实干预的因果效应。
- 任何个人层面的预测、画像或打分都不在模型承诺范围内，也违反产品红线。
