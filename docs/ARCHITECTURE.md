# Architecture

**Applies to:** OpinionLab v1.4.0 · [Docs index](README.md) ·
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
| Hosted demo | generated `site/` | Static GitHub Pages | Browser-local binary preview; no upload |
| Single-container demo | `deploy/docker/demo.Dockerfile` | FastAPI only (no database) | Browser → `/api/v1/demo/*` |
| Docs | `README.md`, `docs/`, `data/`, `examples/` | None | Markdown and tracked screenshots |

The two browser surfaces share one HTML shell and one client. The only
site-specific script is [`site/sim.js`](../site/sim.js), the browser preview
simulator. The local page calls the real demo API. Both backends are normalised
to the same payload before rendering, so the charts, decision brief and exports
cannot drift apart.

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
4. Metrics are aggregated across replicas with Student-*t* 95 % confidence
   intervals; a censored metric such as consensus time excludes replicas that
   never reached the threshold and reports the censoring rate alongside.
5. Runs, manifests, series and reports are written as immutable artifacts.
6. The API/report layer reads artifacts; it never returns per-node opinion
   traces.

The browser demo receives only aggregate series and summary metrics. The
instrument-cluster gauges are derived in the client from those group-level
values; they do not create a second model.

## Demo asset pipeline

There is one source and two build targets:

- **Source:** [`apps/web/`](../apps/web/) contains the HTML shell
  (`index.html`), the client (`app.js`), CSS, i18n and the 3D canvas modules.
  The client reads a `opinionlab-mode` meta tag: `api` calls
  `/api/v1/demo/*`; `static` fetches `templates.json` and uses `sim.js`.
- **Local service UI:** FastAPI serves the same `apps/web/` directory at
  `/api/v1/demo/static`; the page is `/api/v1/demo/app`.
- **Hosted UI:** [`scripts/build_site.py`](../scripts/build_site.py) generates
  `site/index.html`, `site/app.js` and `site/templates.json` from the source and
  the scenario library, copies the shared modules and `sim.js`, and decompresses
  the pinned ECharts bundle into `site/`. `site/index.html` differs only in asset
  URLs, the mode meta tag and the injected `sim.js` script.

The generated files are committed so GitHub Pages can serve `site/` directly,
and a test fails if they differ from a fresh build. Edit `apps/web/`, then run
`make site`; do not edit `site/app.js` or `site/index.html` by hand.
  `scripts/build_static_templates.py` exports the enabled scenario templates;
  `make site` runs both steps. The Pages workflow also triggers on
  `apps/web/**`, `scenarios/**` and the two build scripts so shared UI and
  template changes cannot be missed.

```bash
make site        # assemble site/ for GitHub Pages
make demo        # serve the local full-service UI
make demo-container  # single-container demo with the real engine, no database
```

`site/sim.js` is the tracked site-specific simulator source. The generated
`site/index.html`, `site/app.js` and `site/templates.json` are build outputs.
The shared assets and `site/echarts.min.js` are
generated during the Pages workflow, and the workflow regenerates
`site/templates.json` from the scenario library before packaging. See
[`.github/workflows/pages.yml`](../.github/workflows/pages.yml).

### Instrument cluster

The v1.4.0 hero is a normal DOM/SVG component, not a separate rendering
service:

- `#gaugeCohesion` and `#gaugeTurn` show the current run's cohesion and
  peak-turn values; the SVG rings use a CSS `--gauge` custom property.
- `#trackScene` is a dependency-free canvas projection of a 150-node
  hypergraph. It is decorative telemetry, not a data-accurate network plot.
- The four KPI readouts are filled from the same aggregate response used by the
  charts and metrics cards.
- Both the local and hosted apps receive the same visible version label
  (`BUILD V1.4.0`) and the same four-language copy (English default, Chinese,
  Japanese, German).

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
| `hnle/templates.py` | Scenario library with English/Chinese source labels; the browser adds Japanese/German overlays |
| `apps/api/app/` | Auth, jobs, quotas, connectors, compliance, demo |
| `apps/web/` | The one web client: shell, client, canvas scenes and i18n |
| `site/` | Generated Pages artifact plus the browser simulator |
| `scripts/build_site.py` | Generates the Pages shell, client, templates and ECharts bundle |
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

- Demo only: [`docker-compose.demo.yml`](../docker-compose.demo.yml) and
  `deploy/docker/demo.Dockerfile` (FastAPI, real engine, reports; no database).
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
