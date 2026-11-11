# Architecture

> **In one minute**
>
> - The engine (`packages/hnle`) has no database dependency; the API adds tenancy, jobs and compliance.
> - Reports and APIs expose group-level metrics only; per-node traces are rejected at the boundary.
> - Start with `make demo`, then read `apps/api` and `deploy/`.

OpinionLab is a simulation engine, a service layer and a reporting/deployment kit. The engine has no
database or network dependency, so the same code powers the CLI, the API workers and the public demo.

## Layers

| Layer | Contents | Responsibility |
|---|---|---|
| Engine (`packages/hnle`) | spec, graph, kernels, metrics, Monte Carlo, sweep, calibrate, export, report, templates | deterministic simulation and artifacts |
| Service (`apps/api`) | FastAPI, SQLAlchemy async, auth/RBAC, jobs, connectors, compliance, observability | multi-tenant API, quotas, audit |
| Workers | Celery queues | long-running replicas and exports |
| Demo (`apps/web`, `site/`) | HTML/CSS/JS | public sandbox and hosted preview |
| Deployment | Compose, Helm (CN/global), private offline package | install and operate |

## Data flow

1. A scenario YAML is parsed into a validated `ModelSpec` (the single source of truth).
2. `ModelSpec` + graph seed produce a hypergraph and per-replica RNG streams.
3. Replicas run on the CSR sparse kernel (default) or the event-driven kernel; the event kernel requires integer latency steps.
4. Metrics are aggregated across replicas with 95% confidence intervals.
5. Runs, manifests, series and reports are written as immutable artifacts.
6. The API/report layer reads artifacts; it never returns per-node opinion traces.

## Module map

| Path | Role |
|---|---|
| `hnle/spec.py` | `ModelSpec`, validation, config hash |
| `hnle/graph.py` | random and loaded hypergraphs |
| `hnle/core/kernel.py` | shared conformity map, row normalisation, consensus test |
| `hnle/core/update.py` | node-centric reference kernel |
| `hnle/core/sparse.py` | CSR vectorised kernel |
| `hnle/core/event.py` | event-driven kernel (integer latency) |
| `hnle/metrics.py` | diversity, entropy, cascade, consensus, oscillation |
| `hnle/mc.py` | replicas, Welford aggregation, CIs |
| `hnle/io/` | manifests, artifacts, offline HTML reports |
| `hnle/templates.py` | bilingual scenario library |
| `apps/api/app/` | auth, jobs, quotas, connectors, compliance, demo |

## Invariants

- Updates are **node-centric**: an opinion is written once per step, so hyperedge order cannot change
  the result.
- Each replica gets an independent `SeedSequence` stream for init, latency and decisions.
- Metrics and reports are **group-level only**; any per-node trace is forbidden at the API boundary.
- A spec hash, dataset hash and engine version are recorded in every manifest.
- Equal specs and seeds produce bit-identical series; comparisons use tolerances, never `==`.
- Public demo endpoints are capped and rate-limited; they never write to the database.

## Deployment

- Single host: `docker-compose.yml` (Postgres, Redis, MinIO, API, worker).
- Cluster: `deploy/k8s/helm-cn` and `helm-global` values.
- Air-gapped: `deploy/private/OFFLINE_en.md`.
