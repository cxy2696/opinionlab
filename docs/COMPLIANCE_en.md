# Compliance

## Regions

- `REGION=cn` or `global` controls data residency and the compliance template.
- Cross-region tenant access returns `403 REGION_MISMATCH`.

## Use-case review

- With `USE_CASE_REVIEW_ENABLED=true`, G5 election templates require an org_admin declaration and a
  platform_admin approval.
- Unapproved clones return `403 USE_CASE_NOT_APPROVED`.

## Minimisation and deletion

- Only structural inputs are accepted; raw phone/ID/email/nickname columns are rejected.
- Deleting a dataset cascades graph snapshots, runs, artifacts and sharing mappings; the scenario
  remains but is detached.

## Logging and retention

- Audit logs are append-only and retained for at least 180 days.
- Logs mask emails, keep only the first 8 HMAC characters, and truncate descriptions at 200 chars;
  request bodies and stack traces are not logged in production.

## Red lines

- No endpoint may return single-node opinion trajectories (`NODE_TRACE_FORBIDDEN`).
- Every report must carry the fixed disclaimer; otherwise `DISCLAIMER_MISSING`.
- No election prediction, targeted persuasion or individual scoring.
