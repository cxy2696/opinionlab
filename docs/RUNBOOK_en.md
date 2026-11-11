# Runbook

## Observability and alerts

Prometheus metrics are exposed at `/metrics`:

| Metric | Meaning | Suggested alert |
|---|---|---|
| `opinionlab_api_duration_seconds` | API latency histogram | P95 > 500 ms for 5 min |
| `opinionlab_queue_depth{queue}` | Celery queue depth | > 100 for 10 min |
| `opinionlab_job_duration_seconds` | job duration distribution | P95 > 600 s (`q_normal` soft limit) |
| `opinionlab_replica_failures_total` | replica failures | > 5% failure rate over 5 min |
| `opinionlab_connector_circuit_state{site}` | connector circuit 0/1/2 | OPEN for > 5 min → L1 degrade |

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

## Logs

- structlog JSON: `timestamp/level/trace_id/org_id/user_id/action/duration_ms/status/error_detail/extra`.
- A `trace_id` is created at the request edge and returned as `X-Request-ID`; Celery inherits it.
- Masking: emails (`a***@x.com`), only 8 HMAC chars, descriptions truncated at 200 chars; no bodies
  or stack traces in production.
- File logs rotate daily with 7-day retention; DEBUG only for a bounded window.

## Troubleshooting

1. Page does not load: check Nginx/API and CORS.
2. Submit hangs: inspect `redis-cli XLEN`, worker liveness and queue depth.
3. Job stuck running: compare soft/hard limits; inspect Celery results after hard + 5 min.
4. Suspicious numbers: compare the manifest's `engine_version + spec_sha256` against golden baselines.

## Canary and rollback

1. Deploy one API/worker instance, route 5% of traffic, watch for 30 minutes.
2. Pass: API P95 < 500 ms, job failure < 5%, no abnormal latency lift.
3. Roll back on failure > 20% (15 min), 5xx > 1% (5 min), or any OPT-01-class numerical defect.
4. Rollback: `docker compose pull <previous-tag> && up -d`; revert only reversible migrations with
   `alembic downgrade -1`.

### Tainted run marking

When a numerical or order-dependence defect is found:

```sql
ALTER TABLE runs ADD COLUMN IF NOT EXISTS tainted BOOLEAN NOT NULL DEFAULT FALSE;
UPDATE runs SET tainted = TRUE
WHERE spec_sha256 IN ('<affected-sha-1>', '<affected-sha-2>');
```

Notify the scenario owner; the report page shows a "tainted" banner. Keep the affected runs as
evidence and produce new runs after the fix.
