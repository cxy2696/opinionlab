# 产品演示 / Demo application

![OpinionLab demo](demo.png)

OpinionLab 自带一个无需登录的浏览器演示页，用来快速体验“选场景 → 调参数 → 看演化 → 下载报告”的完整产品流程。

OpinionLab ships a public, no-login browser demo covering the full flow: choose a scenario, tune parameters, watch opinion dynamics, download a report.

## 启动 / Run

```bash
make demo
# 打开 http://127.0.0.1:8000  →  自动跳转到 /api/v1/demo/app
```

演示页只依赖本仓库的引擎与静态资源，不需要 Postgres/Redis；完整服务（登录、场景库、作业队列）见 `docs/ARCHITECTURE.md`。

The demo only needs the engine and static assets; it does not require Postgres/Redis. The full service (auth, scenario library, job queue) is described in the architecture doc.

## 功能 / Features

- 12 个默认场景模板（S1–S6、G1–G4、G6、G7），显示中英双语“提问”
- 可调 `q`、平均时延、步数、副本数、随机种子
- 实时展示多样性曲线
- 指标卡片带 95% 置信区间（多样性、级联 P99、收敛步、吸收态）
- “对比上一次”按钮：同一组参数前后两次运行的差异，并标注置信区间是否重叠
- “下载报告”：单文件离线 HTML（内嵌 ECharts、免责声明、CI 表、假设与局限）
- 所有输出仅群体统计量，不展示任何单节点轨迹

## API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/demo/templates` | 可用模板与默认参数 |
| POST | `/api/v1/demo/simulate` | 运行一次小规模蒙特卡洛，返回指标 + 序列 |
| POST | `/api/v1/demo/report` | 生成单文件 HTML 报告 |
| GET | `/api/v1/demo/echarts.js` | 本地 ECharts bundle（离线可用） |
| GET | `/api/v1/demo/app` | 演示页 |

请求示例：

```bash
curl -s http://127.0.0.1:8000/api/v1/demo/simulate \
  -H 'Content-Type: application/json' \
  -d '{"template_key":"S2","q":1.8,"latency_mu":3,"repeats":8,"seed":42,"steps":120}'
```

## 边界 / Limits

为避免公开接口被滥用，演示模式主动限制：节点 ≤ 400、步数 ≤ 200、副本 ≤ 20，并且只允许启用状态的模板。完整产品没有这些限制，但需要登录与配额。

To keep the public endpoint safe, the demo caps nodes at 400, steps at 200 and replicas at 20, and only exposes enabled templates. The full product has no such caps but requires authentication and quotas.

## 适用场景 / Use cases

- 政策/公关团队做沟通节奏的前期假想推演
- 研究者快速体验模型对 `q`、时延与拓扑的敏感性
- 评审方在浏览器中核对“群体指标 + 置信区间 + 免责声明”的输出形态

- Early what-if exploration for policy/communications teams
- Quick sensitivity checks for researchers
- Reviewers inspecting group metrics, confidence intervals and disclaimers in a browser
