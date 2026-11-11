# Air-gapped private delivery

## Contents

- API and worker images (`opinionlab-api`, `opinionlab-worker`)
- Helm chart values for CN/global
- Alembic migrations
- Checksums and a signed bill of materials
- This runbook and the compliance/model card documents

## Steps

1. Load images into the internal registry.
2. Create secrets for database, Redis, JWT and encryption keys.
3. Run migrations with `alembic upgrade head`.
4. Install the chart with the private values file.
5. Verify `/health`, `/metrics` and a demo run.
6. Register the installation with the platform admin.

## Verification

- Image digests match the bill of materials.
- `/health` returns 200 and `/metrics` exposes the expected series.
- A smoke scenario runs end-to-end and produces a report with the disclaimer.
- Cross-region access is blocked.

## Rollback

- Keep the previous image digests and values file.
- Roll back with Helm; revert migrations only when the downgrade is reversible.
- Mark affected runs tainted if a numerical defect is found.
