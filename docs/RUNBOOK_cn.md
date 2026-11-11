# 运维手册 / Runbook

> **一分钟版本**
>
> - 先看 `/metrics`：API P95、队列深度、副本失败率、连接器熔断。
> - 回滚用上一个镜像 tag；数据库只做可逆迁移。
> - 发现数值缺陷时标记 tainted，保留证据并重跑。

## 观测与告警 / Observability & alerts
Prometheus 指标由 API 暴露在 `/metrics`：

| 指标 | 含义 | 告警建议 |
|---|---|---|
| `opinionlab_api_duration_seconds` | API 时延直方图 | P95 > 500ms 持续 5 分钟 |
| `opinionlab_queue_depth{queue}` | Celery 队列深度 | > 100 持续 10 分钟 |
| `opinionlab_job_duration_seconds` | 作业耗时分布 | P95 > 600s（q_normal soft limit） |
| `opinionlab_replica_failures_total` | 副本失败数 | 5 分钟失败率 > 5% |
| `opinionlab_connector_circuit_state{site}` | 连接器熔断状态 0/1/2 | 持续 OPEN > 5 分钟 -> L1 降级 |

Alert rules (Prometheus):
```yaml
- alert: ApiP95High
  expr: histogram_quantile(0.95, sum(rate(opinionlab_api_duration_seconds_bucket[5m])) by (le)) > 0.5
  for: 5m
- alert: QueueDepthHigh
  expr: opinionlab_queue_depth > 100
  for: 10m
- alert: ReplicaFailureRate
  expr: rate(opinionlab_replica_failures_total[5m]) > 0.05
- alert: ConnectorOpen
  expr: opinionlab_connector_circuit_state > 1
  for: 5m
```

## 日志 / Logs
- structlog JSON：`timestamp/level/trace_id/org_id/user_id/action/duration_ms/status/error_detail/extra`
- 请求入口生成 `trace_id`，响应头 `X-Request-ID` 返回；Celery 任务从 headers 继承。
- 脱敏：邮箱掩码（`a***@x.com`）、HMAC 只保留前 8 位、description 截断 200 字符；生产不记录正文与堆栈。
- 文件日志按天轮转，保留 7 天（`backupCount=7`）；DEBUG 仅限时开启。

## 排障 / Troubleshooting
1. 打不开：检查 Nginx/API 与 CORS。
2. 提交无反应：`redis-cli XLEN` 与 worker 存活、队列深度。
3. 作业一直 running：比对 soft/hard limit，> hard+5min 主动查 Celery 结果。
4. 结果异常：取 manifest 比对 `engine_version + spec_sha256`，检查 golden 基线漂移。

## 金丝雀与回滚 / Canary & rollback
1. 新版本先部署 1 个 API/worker 实例，路由 5% 流量，观察 30 分钟。
2. 通过指标：API P95 < 500ms、作业失败率 < 5%、`opinionlab_api_duration_seconds` 无异常抬升。
3. 回滚触发：失败率 > 20%（15 分钟）、5xx > 1%（5 分钟）、发现 OPT-01 类数值缺陷。
4. 回滚：`docker compose pull <previous-tag> && up -d`；数据库仅可逆迁移 `alembic downgrade -1`。

### Tainted 标记流程 / Tainted run marking
发现引擎缺陷（数值不可复现/顺序依赖）时：
```sql
ALTER TABLE runs ADD COLUMN IF NOT EXISTS tainted BOOLEAN NOT NULL DEFAULT FALSE;
UPDATE runs SET tainted = TRUE
WHERE spec_sha256 IN ('<affected-sha-1>', '<affected-sha-2>');
```
- 通知导出过相关报告的 scenario_owner，报告页显示 "tainted" 提示。
- 受影响 run 不删除，保留复现证据；重新运行生成新 run。
