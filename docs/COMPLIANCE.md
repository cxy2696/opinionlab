# Compliance

**Applies to:** OpinionLab v1.3.1 · [Docs index](README.md) ·
[Changelog](../CHANGELOG.md)

This page states the operational policy shipped with the service. It is the
reference for deployment review; the model boundaries and prohibited uses are
in the [Model card](MODEL_CARD.md).

## Regions

- `REGION=cn` or `global` controls data residency and cross-region isolation.
- Cross-region tenant access returns `403 REGION_MISMATCH`.
- The deployment values in [`deploy/k8s/`](../deploy/k8s/) show the CN and
  global layouts.

## Use-case review

- With `USE_CASE_REVIEW_ENABLED=true` (the default), G5 election templates
  require an `org_admin` declaration and a `platform_admin` approval.
- Unapproved clones return `403 USE_CASE_NOT_APPROVED`.
- G5 is disabled in the public template library; see the
  [Use cases template library](USE_CASES.md#template-library) for the enabled
  research templates and [Demo](DEMO.md) for the browser limits.

## Minimisation and deletion

- Only structural inputs are accepted; raw phone/ID/email/nickname columns are
  rejected by the ingest policy.
- Input user IDs are HMAC-SHA256 pseudonymised before they reach the engine.
- Deleting a dataset cascades graph snapshots, runs, artifacts and sharing
  mappings; the scenario remains but is detached.

## Logging and retention

- Audit logs are append-only and retained for at least 180 days.
- Logs mask emails, keep only the first 8 HMAC characters, and truncate
  descriptions at 200 chars; request bodies and stack traces are not logged in
  production.
- File logs rotate daily with a 7-day retention window. See the
  [Runbook](RUNBOOK.md#logs) for the operational view.

## Optional generative assist

- Ollama narration is off by default (`OLLAMA_ENABLED=true` to enable) and is
  never used for metrics, conclusions or individual prediction.
- Output must be labelled “AI-assisted explanation, not a conclusion” and keep
  engine numbers and disclaimers authoritative.
- No third-party data transfer; the default endpoint is local
  `127.0.0.1:11434`.
- The hosted demo cannot reach a local Ollama instance.

## Red lines

- No endpoint may return single-node opinion trajectories
  (`NODE_TRACE_FORBIDDEN`).
- Every report must carry the fixed disclaimer; otherwise `DISCLAIMER_MISSING`.
- No election prediction, targeted persuasion or individual scoring.

## Enforcement

The policy is exercised by:

- [`tests/test_compliance.py`](../tests/test_compliance.py): region mismatch,
  G5 approval, deletion cascade, report red lines.
- [`tests/test_observability.py`](../tests/test_observability.py): masking and
  Prometheus surface.
- [`tests/test_report_guardrails.py`](../tests/test_report_guardrails.py):
  disclaimer and report gates.

## Related documents

- [Model card](MODEL_CARD.md): capabilities, limits and prohibited uses.
- [Runbook](RUNBOOK.md): observability, rollback and tainted-run handling.
- [Architecture](ARCHITECTURE.md): service boundaries and data flow.
- [Air-gapped delivery](../deploy/private/OFFLINE.md): offline verification.
