# Architecture

**Applies to:** OpinionLab v1.3.1 · [Docs index](README.md) ·
[Changelog](../CHANGELOG.md)

OpinionLab is a simulation engine, a service layer and a reporting/deployment
kit. The engine has no database or network dependency, so the same engine code
powers the CLI and the API workers. The hosted browser demo uses a separate,
dependency-free simulator; the local demo calls the real engine through the API.

## System context

| Surface | Code | Runtime dependency | Data path |
|---|---|---|---|
| CLI | `packages/hnle/` | None beyond the Python package | Writes immutable artifacts under `runs/` |
| Service API | `apps/api/` | FastAPI, PostgreSQL, Redis, Celery, object storage | Jobs → engine workers → artifacts and reports |
| Local demo | `apps/web/` served by the API | FastAPI demo router | Browser → `/api/v1/demo/*` |
| Hosted demo | `site/` + shared `apps/web/` assets | Static GitHub Pages | Browser-local binary simulation; no upload |
| Docs | `README.md`, `docs/`, `data/`, `examples/` | None | Markdown and tracked screenshots |

The two browser surfaces share the cockpit styling and 3D canvas modules, and
the instrument-cluster markup is kept aligned in both page shells. The hosted
page uses
[`site/sim.js`](../site/sim.js); the local page calls the real demo API.

## Layers

| Layer | Contents | Responsibility |
|---|---|---|
| Engine (`packages/hnle`) | spec, graph, kernels, metrics, Monte Carlo, sweep, calibrate, export, report, templates | Deterministic simulation and artifacts |
| Service (`apps/api`) | FastAPI, SQLAlchemy async, auth/RBAC, jobs, connectors, compliance, observability | Multi-tenant API, quotas, audit |
| Workers | Celery queues | Long-running replicas and exports |
| Demo (`apps/web`, `site/`) | HTML/CSS/JS, 3D canvases, browser simulator | Public sandbox and hosted preview |
| Deployment | Compose, Helm values (CN/global), private offline package | Install and operate |

## Data flow

1. A scenario YAML is parsed into a validated `ModelSpec` (the single source of
   truth).
2. `ModelSpec` + graph seed produce a hypergraph and per-replica RNG streams.
3. Replicas run on the CSR sparse kernel (default) or the event-driven kernel;
   the event kernel requires integer latency steps.
4. Metrics are aggregated across replicas with 95 % confidence intervals.
5. Runs, manifests, series and reports are written as immutable artifacts.
6. The API/report layer reads artifacts; it never returns per-node opinion
   traces.

The browser demo receives only aggregate series and summary metrics. The
instrument-cluster gauges are derived in the client from those group-level
values; they do not create a second model.

## Demo asset pipeline

The web UI has two build targets:

- **Local service UI:** [`apps/web/index.html`](../apps/web/index.html) loads
  `/api/v1/demo/static/style.css` and the JavaScript modules
  (`app.js`, `scene.js`, `galaxy.js`, `field3d.js`, `particles.js`, `i18n.js`)
  from the FastAPI static mount. `app.js` calls the demo API.
- **Hosted UI:** [`site/index.html`](../site/index.html) is the page shell;
  `site/app.js` and `site/sim.js` implement the browser-only path.
  `scripts/build_site.py` copies the shared CSS/JS modules from `apps/web/` and
  decompresses the pinned ECharts bundle into `site/`.
  `scripts/build_static_templates.py` exports the enabled scenario templates;
  `make site` runs both steps. The Pages workflow also triggers on
  `apps/web/**`, `scenarios/**` and the two build scripts so shared UI and
  template changes cannot be missed.

```bash
make site        # assemble site/ for GitHub Pages
make demo        # serve the local full-service UI
```

`site/index.html`, `site/app.js`, `site/sim.js` and `site/templates.json` are
tracked site-specific sources. The shared assets and `site/echarts.min.js` are
generated during the Pages workflow, and the workflow regenerates
`site/templates.json` from the scenario library before packaging. See
[`.github/workflows/pages.yml`](../.github/workflows/pages.yml).

### Instrument cluster

The v1.3.1 hero is a normal DOM/SVG component, not a separate rendering
service:

- `#gaugeCohesion` and `#gaugeTurn` show the current run's cohesion and
  peak-turn values; the SVG rings use a CSS `--gauge` custom property.
- `#trackScene` is a dependency-free canvas projection of a 150-node
  hypergraph. It is decorative telemetry, not a data-accurate network plot.
- The four KPI readouts are filled from the same aggregate response used by the
  charts and metrics cards.
- Both the local and hosted apps receive the same visible version label
  (`BUILD V1.3.1`) and the same bilingual copy.

## Module map

| Path | Role |
|---|---|
| `hnle/spec.py` | `ModelSpec`, validation, config hash |
| `hnle/graph.py` | Random, loaded and ingested hypergraphs; connected components |
| `hnle/core/kernel.py` | Shared conformity map, row normalisation, consensus test |
| `hnle/core/update.py` | Node-centric reference kernel |
| `hnle/core/sparse.py` | CSR vectorised kernel |
| `hnle/core/event.py` | Event-driven kernel (integer latency) |
| `hnle/metrics.py` | Diversity, entropy, cascade, consensus, oscillation |
| `hnle/mc.py` | Replicas, Welford aggregation, CIs |
| `hnle/io/` | Manifests, artifacts, offline HTML reports |
| `hnle/templates.py` | Scenario library with English/Chinese display labels |
| `apps/api/app/` | Auth, jobs, quotas, connectors, compliance, demo |
| `apps/web/` | Local demo UI and canvas scenes |
| `site/` | Hosted shell, browser simulator and scenario export |
| `scripts/build_site.py` | Shared-asset and ECharts assembly for Pages |
| `conformance/` | Shared binary fixture |
| `tests/` | Unit, integration, golden, frontend and documentation checks |

## Invariants

- Updates are **node-centric**: an opinion is written once per step, so
  hyperedge order cannot change the result.
- Each replica gets an independent `SeedSequence` stream for init, latency and
  decisions.
- Metrics and reports are **group-level only**; any per-node trace is forbidden
  at the API boundary.
- A spec hash, dataset hash and engine version are recorded in every manifest.
- Equal specs and seeds produce bit-identical series; comparisons use
  tolerances, never `==`.
- Public demo endpoints are capped and rate-limited; they never write to the
  database.
- The local and hosted UIs may render differently, but their labels, disclaimer
  and group-level metric definitions stay aligned.

## Deployment

- Single host: [`docker-compose.yml`](../docker-compose.yml) (Postgres, Redis,
  MinIO, API, worker).
- Cluster: Helm values for the CN and global layouts in
  [`deploy/k8s/helm-cn`](../deploy/k8s/helm-cn) and
  [`deploy/k8s/helm-global`](../deploy/k8s/helm-global). The chart templates are
  supplied by the deployment environment.
- Air-gapped: [`deploy/private/OFFLINE.md`](../deploy/private/OFFLINE.md).

Release image tags in the Helm values are kept in step with the visible product
version. For operational checks, see [Runbook](RUNBOOK.md), [Capacity](capacity-report.md)
and [Compliance](COMPLIANCE.md).
