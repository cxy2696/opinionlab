# OpinionLab 模型卡 / Model Card

> **一分钟版本**
>
> - 能做：群体层面的情景推演、95% CI、可复现报告。
> - 不能做：个人预测、画像、选举预测、定向说服。
> - 默认不调用生成式模型；Ollama 辅助解读默认关闭且必须标注。

## 能力 / Capabilities
- 超图群体互动 + 非线性从众 `q` + 异质时延的舆论演化仿真。
- 输出群体层面指标（多样性、熵、极化、级联分位、收敛/振荡）及 95% 置信区间。
- Hypergraph group interaction, non-linear conformity `q` and heterogeneous latency.
- Group-level metrics (diversity, entropy, polarisation, cascade quantiles,
  convergence/oscillation) with 95% confidence intervals.

## 局限 / Limitations
- 不模拟平台推荐算法、媒体议程、线下行为与真实价格反馈。
- 参数与拓扑来自给定数据，结论只对假设空间成立。
- Does not model recommender systems, media agenda, offline behaviour or prices.
- Conclusions hold only inside the declared assumption space.

## 禁止用途 / Prohibited uses
- 禁止对真实个人进行观点预测、画像或打分。
- 禁止用于选举预测、定向 Persuasion 或任何违反当地法律的用途。
- No prediction, profiling or scoring of real individuals.
- No election forecasting, targeted persuasion, or any unlawful use.

## 数据与合规 / Data & compliance
- 输入 ID 经 HMAC-SHA256 假名化；PII 列直接拒绝。
- 默认留存 180 天，支持 dataset 删除级联清理。
- 中国大陆与欧盟双区部署，跨区租户数据访问返回 403。
- IDs are HMAC-SHA256 pseudonymised; PII columns are rejected.
- Default retention is 180 days with cascading dataset deletion.
- CN/EU dual-region deployment; cross-region tenant access returns 403.

## 生成式内容 / Generative content
引擎不调用生成式模型计算指标或产出结论。可选 Ollama 仅用于“辅助解读”，默认关闭、必须显式启用，输出会标注“AI 辅助解释，不是结论”，且需人工复核；它不改变任何指标、决策或报告数值。
The platform does not call generative models for conclusions; any future generated
section must be labelled and human-reviewed.
