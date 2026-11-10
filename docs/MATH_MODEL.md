# 数学模型 / Math model

## 公式与代码逐条对应 / Formula-to-code map
| 公式 / Formula | 代码 / Code |
|---|---|
| `S_x(e) = Σ_{j∈e} α_j · 1(X_j=x)` | `core/update.py::edge_distributions`、`core/sparse.py::_node_probabilities` |
| `P(X_i=1|e) = S_1^q / (S_0^q + S_1^q)` | 同上（多立场时对每个 v） |
| 就绪 `t - T_i ≥ L_i` | `core/update.py::run_simulation`（`ready` 掩码） |
| 节点聚合 `mean/max/size_weighted` | `aggregate_node_probabilities`、CSR 分支 |
| `diversity = 1 - max_v share_v` | `metrics.diversity` |
| `entropy = -Σ p ln p`（实现用 bit） | `metrics.shannon_entropy` |
| 振荡：FFT 主频占比 / 过零率 / lag-k 自相关 | `metrics.fft_power_ratio` 等 |
| 收敛 `time_to_consensus`、吸收态 | `metrics.time_to_consensus` / `consensus_stability` |
| 单副本成本 `c·nnz·steps` | `hnle/capacity.py`（实测 c≈1.5e-8） |

## 与论文公式 (3) 的差异 / Sampling vs argmax
论文写 `argmax_X P(X_i(t+1)=X|e)`（确定性），上游代码实际是 `random() < p1`（蒙特卡洛）。
V1 将两者都做成显式选项：

- `decision_rule=stochastic`（默认，与上游动力学一致）
- `decision_rule=argmax`（论文确定性规则）
- `decision_rule=threshold`（`p1 ≥ τ` 才切换）

报告中必须注明所用规则；两者动力学性质不同（确定性规则无采样噪声）。

## 时延与更新 / Latency & update
- 离散引擎：`t - last_change_time[i] ≥ L_i` 才参与更新；步末原子写回。
- 事件引擎：每次评估后按 `L_i` 重新调度（连续时间用最小堆；整数时延用时间桶）。
- `L_i≡1` 时两引擎逐位一致（`tests/test_engine_equivalence.py`）。

## 数值可复现 / Numerics
- 根种子 → `SeedSequence.spawn(3)` 分流 init/latency/decision，避免流间耦合。
- 超边先 `sorted` 再聚合，浮点求和顺序固定，置换不变可达 `atol=0`。
- 指标 float64；比较统一 `numpy.testing.assert_allclose`，禁止 `==`。
