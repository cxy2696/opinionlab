# Air-gapped private delivery

**Applies to:** OpinionLab v1.4.0 · [Docs index](../../docs/README.md) ·
[Runbook](../../docs/RUNBOOK.md) · [Changelog](../../CHANGELOG.md)

## Contents

- API and worker images (`opinionlab-api`, `opinionlab-worker`)
- Helm values for the CN and global layouts
  (`deploy/k8s/helm-cn`, `deploy/k8s/helm-global`); use the chart templates
  supplied with your deployment environment
- Alembic migrations (`migrations/`)
- Checksums and a signed bill of materials
- The [compliance](../../docs/COMPLIANCE.md),
  [model card](../../docs/MODEL_CARD.md) and
  [runbook](../../docs/RUNBOOK.md) documents

The default image tag in the Helm values for this release is `1.4.0`; pin the
exact digest in the delivery manifest before installation.

## Steps

1. Load images into the internal registry.
2. Create runtime secrets from the keys in [`.env.example`](../../.env.example);
   replace every development default (database password, JWT secret, HMAC salt)
   before go-live.
3. Run migrations with `alembic upgrade head`.
4. Install the deployment chart with the private values file.
5. Verify `/health`, `/metrics` and a demo run.
6. For a demo-only host, load the single-container image built from
   `deploy/docker/demo.Dockerfile` and run `docker compose -f
   docker-compose.demo.yml up -d`; it needs no PostgreSQL, Redis or MinIO.
6. Register the installation with the platform admin.

## Verification

- Image digests match the bill of materials.
- `/health` returns 200 and `/metrics` exposes the expected series.
- A smoke scenario runs end-to-end and produces a report with the disclaimer.
- Cross-region access is blocked; verify `403 REGION_MISMATCH` before go-live.
- The browser demo is reachable at `/api/v1/demo/app` and the OpenAPI page is
  available at `/docs` if the deployment exposes it.

## Rollback

- Keep the previous image digests and values file.
- Roll back with Helm; revert migrations only when the downgrade is reversible.
- Mark affected runs tainted if a numerical defect is found; see the
  [Runbook](../../docs/RUNBOOK.md#tainted-run-marking).
- Re-run `make check` and the release benchmark before redeploying.

## Related documents

- [Architecture](../../docs/ARCHITECTURE.md): layers and deployment topology.
- [Capacity](../../docs/capacity-report.md): sizing and load-test pass criteria.
- [Compliance](../../docs/COMPLIANCE.md): regional, review and retention rules.
