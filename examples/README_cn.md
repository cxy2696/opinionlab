# 示例 / Examples

两个最小案例，直接使用模板与引擎 API，不需要数据库或 API 服务。

Two minimal examples using templates and the engine directly; no database or API server needed.

## 1. 辟谣时机 / Debunk timing

```bash
uv run python examples/rumor_timing.py --repeats 8
```

对比 T+2 / T+12 / T+24 三个投放时点的最终正向占比与 95% CI。若 CI 重叠，说明在当前副本数与假设下无法断言时点效果。

Compares final positive share and 95% CI for debunking at T+2, T+12 and T+24. Overlapping CIs mean the timing effect is not established at this sample size.

## 2. 社区议事中的从众强度 / Conformity in a community discussion

```bash
uv run python examples/community_consensus.py --repeats 6
```

改变 `q`，观察多样性、收敛步与吸收态；用来判断讨论是在形成共识，还是被从众压力压成单一声音。

Vary `q` and watch diversity, consensus step and absorption to distinguish genuine consensus from conformity pressure.

## 更多场景 / More scenarios

- `docs/USE_CASES_cn.md`：危机沟通、社区议事、组织变革、产品发布、学术复现等具体案例
- `scenarios/`：15 个可运行模板
- `make demo`：在浏览器中交互体验
