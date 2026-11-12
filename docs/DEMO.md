# Demo application

**Applies to:** OpinionLab v1.3.1 · [Docs index](README.md) ·
[Changelog](../CHANGELOG.md)

OpinionLab includes a no-login browser sandbox for the full loop: choose a
scenario, tune parameters, watch the group evolve and export the result. The
hosted page runs a lightweight binary simulator entirely in the browser. The
local service uses the real engine.

[![OpinionLab v1.3.1 instrument cluster](demo.png)](demo.png)

*Instrument cluster, live opinion stage and readouts in the v1.3.1 demo. The
values shown are the S2 preview before the first run.*

## Live and local

| Surface | Entry point | Differences |
|---|---|---|
| Hosted | <https://cxy2696.github.io/opinionlab/> | No install; local binary simulation; CSV export; no server-side report |
| Local full service | `make demo` → <http://127.0.0.1:8000/api/v1/demo/app> | Real engine; multiple stances; offline HTML report; interactive API docs at <http://127.0.0.1:8000/docs> |

```bash
make setup
make demo
# http://127.0.0.1:8000 -> /api/v1/demo/app
```

`make setup` creates a local `.env` from [`.env.example`](../.env.example) if
needed and, when Docker is available, starts PostgreSQL, Redis and MinIO and
runs the migrations. The hosted page uploads nothing. The local service uses
the engine and can serve reports, while the hosted page stays a lightweight
preview.

## Interface tour

The v1.3.1 product view keeps the cockpit shell and adds a dashboard-style
instrument cluster above the working controls.

| Area | What it shows | How it is computed |
|---|---|---|
| **Cohesion gauge** | Final agreement index | `100 × (1 − mean final diversity)` across replicas |
| **Live 3D stage** | Opinion network, node/step/divergence telemetry | Projected 150-node hypergraph; decorative tracking brackets |
| **Peak-turn gauge** | Largest single-step switching share | Maximum of the displayed run's cascade series |
| **Observed steps** | Observation window | Submitted `steps` value |
| **Mean majority** | Mean step to an 80 % majority | Mean over replicas that reached a majority; censored replicas are excluded |
| **Peak turn** | Same peak as the right gauge | Percentage of nodes changing stance in one step |
| **95 % confidence** | Half-width of the final-diversity interval | `(ci95_hi − ci95_lo) / 2` of final diversity |

The cluster starts with the S2 defaults (`PREVIEW // S2 DEFAULT`). Clicking
**Run** scrolls to the control deck, runs the current configuration and updates
the gauges and readouts (`LIVE RUN // n REPLICAS`). The status bar still shows
the UTC build clock; the cluster clock is local time.

Below the hero:

- **Control deck:** scenario, question, `q`, latency, steps, replicas, seed,
  presets, validation and the Run button.
- **Results and decision brief:** verdict, summary, timing nodes, simulated
  window, follow-up checks and the mandatory caveat.
- **3D telemetry array:** opinion terrain, cascade bars and stance cloud.
- **Linked charts:** diversity, opinion shares and cascade.
- **Replay, comparison and export:** replay the series, compare a run with the
  previous run, copy a parameter link, and export CSV (hosted) or an HTML report
  (local service).

### Screenshots

| View | Image |
|---|---|
| Product hero, English default | [`demo.png`](demo.png) |
| Japanese UI | [`demo-ja.png`](demo-ja.png) |
| German UI | [`demo-de.png`](demo-de.png) |
| 3D telemetry after a run | [`telemetry-3d.png`](telemetry-3d.png) |

The interface defaults to **English** and ships with **Chinese**, **Japanese**
and **German** translations. Use the language selector in the top right of the
instrument cluster, or append `?lang=en`, `?lang=zh`, `?lang=ja` or `?lang=de`.
The selector shows native language names, updates the document language and
locale-aware date, and keeps the choice in local storage and in shareable run
links. A completed run can also be shared with the parameter query string, and
`?run=1` runs the current scenario on load.

## Features

- A dashboard-style product hero: two circular gauges, a live 3D opinion stage
  and four readouts (steps, mean majority, peak turn, 95 % CI); the instruments
  update after every run.
- Four UI languages with English as the default: English, Chinese, Japanese
  and German, including translated scenario questions, chart labels, metrics,
  summaries and decision briefs.
- 16 scenario templates (15 enabled; G5 is gated) with the question each one
  helps answer.
- Inline explanations for every parameter, hover tips and one-click presets.
- A 3D telemetry array: dotted opinion terrain, elevated cascade bars and a
  rotating stance cloud, with live peak/current stats, a legend and hover
  readouts on the bars.
- Three linked charts with particle overlays: diversity flow, drifting opinion
  particles and cascade bursts.
- A cockpit shell with a system status bar, numbered decks, UTC clock, telemetry
  and responsive layouts for desktop, tablet and phone.
- A decision brief: what the run informs, key timing nodes, a simulated window,
  follow-up checks and a caveat.
- Replay, comparison with the previous run, CSV export (hosted) or a single-file
  HTML report (local service), and shareable parameter links.
- A 3D industrial tracker with tracking brackets and telemetry.

## How to read the charts

| Chart | What to look for |
|---|---|
| Diversity | Solid line is this run; dashed line is the replica median; the band is 10–90 %. A wide band means the result depends on randomness. |
| Opinion shares | How the share of each stance changes; the stacked area shows which stance is winning over time. |
| Cascade | Share of people changing in each step; spikes mark sudden shifts. |

- `n` is the number of replicas aggregated. Do not over-read intervals when
  `n < 30`.
- The consensus step counts only replicas that reached a majority; if none did,
  the card says so. The censoring state is preserved rather than reported as
  zero.
- The confidence interval is a Student-*t* interval, not a normal
  approximation; see the [Math model](MATH_MODEL.md#6-monte-carlo-estimator-and-intervals).

## Decision brief and timing

Each run reports:

1. What decision it can inform (for example, timing and strength of debunking).
2. Key timing nodes: cascade take-off, peak, majority and this run's
   intervention.
3. A simulated action window, for example “about two reaction cycles before the
   peak (steps 14–20)”.
4. Follow-up checks: rerun with one timing change, compare CIs, raise replicas,
   calibrate on real data.
5. A caveat: timing advice is a simulated window, not a forecast of real event
   timing.

The brief appears in the demo and in the local service's downloaded HTML report.

## API

The local service exposes the demo API at `/api/v1/demo`; interactive OpenAPI
docs are at `/docs`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/demo/templates` | Enabled templates and defaults |
| POST | `/api/v1/demo/simulate` | One small Monte Carlo run, metrics and series |
| POST | `/api/v1/demo/report` | Single-file HTML report |
| POST | `/api/v1/demo/narrate` | Optional Ollama narration (off by default) |
| GET | `/api/v1/demo/echarts.js` | Local ECharts bundle |
| GET | `/api/v1/demo/app` | The demo page |

Service-level endpoints:

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Service health |
| GET | `/metrics` | Prometheus metrics |
| GET | `/docs` | Interactive OpenAPI documentation |

```bash
curl -s http://127.0.0.1:8000/api/v1/demo/simulate \
  -H 'Content-Type: application/json' \
  -d '{"template_key":"S2","q":1.8,"latency_mu":3,"repeats":8,"seed":42,"steps":120}'
```

## Ollama-assisted narration

The local full service can optionally call a local Ollama model to restate a
run and suggest two next experiments.

- Off by default: set `OLLAMA_ENABLED=true` and run
  `ollama serve && ollama pull llama3.2`.
- It reads engine numbers only; it computes no metrics, predicts no individuals
  and does not decide.
- Output is labelled “AI-assisted explanation, not a conclusion”.
- The hosted demo cannot call local Ollama; the button explains this.

```bash
ollama serve
ollama pull llama3.2
OLLAMA_ENABLED=true make demo
```

## Limits and operations

| Item | Default | Notes |
|---|---|---|
| `DEMO_MAX_NODES` | 400 | Node cap for the public demo |
| `DEMO_MAX_STEPS` | 200 | Step cap |
| `DEMO_MAX_REPEATS` | 20 | Replica cap |
| Rate limits | 100 global / 20 IP / 30 user / 200 org rps | Shared token buckets |
| Observability | `/metrics` | API latency, queue depth, replica failures |

- The public endpoints do not require login and do not write to the database.
- The four-language UI covers the on-screen controls and result narrative.
  Optional Ollama narration follows the selected language; the downloadable
  HTML report remains bilingual English/Chinese.
- Change caps in `.env` and restart the API.
- The assets are split for maintainability: the site shell is
  `site/index.html`, `site/app.js`, `site/sim.js` and `site/templates.json`; the
  shared UI pieces are `style.css`, `scene.js`, `galaxy.js`, `field3d.js`,
  `particles.js` and `i18n.js`. `site/echarts.min.js` is assembled locally by
  [`scripts/build_site.py`](../scripts/build_site.py).
- The local page is served from [`apps/web/`](../apps/web/); the demo API is in
  [`apps/api/app/demo.py`](../apps/api/app/demo.py).

## Use cases and related reading

- Early what-if exploration for policy and communications teams.
- Quick sensitivity checks for researchers.
- Reviewing group metrics, confidence intervals and disclaimers in a browser.

See [Use cases](USE_CASES.md) for the questions, [Model card](MODEL_CARD.md)
for the product boundary, and [Architecture](ARCHITECTURE.md) for the data
flow behind the interface.
