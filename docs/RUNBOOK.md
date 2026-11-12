# Runbook

**Applies to:** OpinionLab v1.4.0 · [Docs index](README.md) ·
[Changelog](../CHANGELOG.md)

## Service checks

The local service reads `.env` if present; start from
[`.env.example`](../.env.example) and replace development secrets before
sharing the host. Use a random `JWT_SECRET` of at least 32 bytes. Run
`uv run pip-audit` before a release; the weekly workflow uses the same command.

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/metrics | head
# interactive API docs:
# http://127.0.0.1:8000/docs
```

## Observability and alerts

Prometheus metrics are exposed at `/metrics`:

| Metric | Meaning | Suggested alert |
|---|---|---|
| `opinionlab_api_duration_seconds` | API latency histogram | P95 > 500 ms for 5 min |
| `opinionlab_queue_depth{queue}` | Celery queue depth | > 100 for 10 min |
| `opinionlab_job_duration_seconds` | Job duration distribution | P95 > 600 s (`q_normal` soft limit) |
| `opinionlab_replica_failures_total` | Failed replicas by reason | > 0.05 failures/s over 5 min |
| `opinionlab_connector_circuit_state{site}` | Connector circuit 0/1/2 | OPEN (`> 1`) for > 5 min, then L1 degrade |

```yaml
- alert: ApiP95High
  expr: histogram_quantile(0.95, sum(rate(opinionlab_api_duration_seconds_bucket[5m])) by (le)) > 0.5
  for: 5m
- alert: QueueDepthHigh
  expr: opinionlab_queue_depth > 100
  for: 10m
- alert: ReplicaFailures
  expr: sum(rate(opinionlab_replica_failures_total[5m])) > 0.05
  for: 5m
- alert: ConnectorOpen
  expr: opinionlab_connector_circuit_state > 1
  for: 5m
```

Capacity pass lines and load scenarios are in the
[Capacity report](capacity-report.md).

## Logs

- structlog JSON:
  `timestamp/level/trace_id/org_id/user_id/action/duration_ms/status/error_detail/extra`.
- A `trace_id` is created at the request edge and returned as `X-Request-ID`;
  Celery inherits it.
- Masking: emails (`a***@x.com`), only 8 HMAC chars, descriptions truncated at
  200 chars; no bodies or stack traces in production.
- File logs rotate daily with 7-day retention; DEBUG only for a bounded window.
- Retention and deletion rules are in [Compliance](COMPLIANCE.md).

## Troubleshooting

1. Page does not load: check Nginx/API and CORS.
2. Submit hangs: inspect `redis-cli XLEN`, worker liveness and queue depth.
3. Job stuck running: compare soft/hard limits; inspect Celery results after
   hard + 5 min.
4. Suspicious numbers: compare the manifest's `engine_version + spec_sha256`
   against golden baselines and re-run `make check`.
5. Hosted demo looks stale: confirm the Pages workflow ran after the latest
   `apps/web/` or scenario change. `site/index.html`, `site/app.js` and
   `site/templates.json` are generated; run `make site` and redeploy if the
   drift test fails. The hosted page is static and does not use the API.
6. Local demo looks stale: rebuild/restart the service; `apps/web/` is served
   directly by the API, so a running server needs a reload after UI edits.
7. Users report a missing or negative confidence bound: bounded intervals are
   clamped for display only; check the stored `metrics` value and the censoring
   rate first.
8. Users ask why a result is labelled `underpowered` or `censored`: read the
   `quality` block in the API response and the metric dictionary in the
   [User guide](USER_GUIDE.md#metric-dictionary). Neither flag is an engine
   failure.

## Canary and rollback

1. Deploy one API/worker instance, route 5 % of traffic and watch for 30
   minutes.
2. Pass: API P95 < 500 ms, job failure < 5 %, no abnormal latency lift.
3. Roll back on failure > 20 % (15 min), 5xx > 1 % (5 min), or any
   OPT-01-class numerical defect.
4. Rollback: restore the previous image tag or digest, then run
   `docker compose pull && docker compose up -d`. Revert only reversible
   migrations with `alembic downgrade -1`.

### Tainted run marking

When a numerical or order-dependence defect is found:

```sql
ALTER TABLE runs ADD COLUMN IF NOT EXISTS tainted BOOLEAN NOT NULL DEFAULT FALSE;
UPDATE runs SET tainted = TRUE
WHERE spec_sha256 IN ('<affected-sha-1>', '<affected-sha-2>');
```

Notify the scenario owner. Keep the affected runs as evidence and produce new
runs after the fix. The `runs.tainted` field is stored on the run; any surface
that lists runs must present the tainted state before the result is reused.

## Related documents

- [Architecture](ARCHITECTURE.md): service boundaries and data flow.
- [Capacity](capacity-report.md): job examples and load-test pass criteria.
- [Compliance](COMPLIANCE.md): retention, masking and red lines.
- [Deployment values](../deploy/k8s/): CN and global layouts.
