# Demo application

**Applies to:** OpinionLab v1.4.0 · [Docs index](README.md) ·
[Changelog](../CHANGELOG.md)

OpinionLab includes a no-login browser sandbox for the full loop: choose a
scenario, tune parameters, watch the group evolve and export the result. The
hosted page runs a lightweight preview simulator in the browser. The local
service runs the real Python engine and adds offline reports and optional local
Ollama narration.

[![OpinionLab v1.4.0 instrument cluster](demo.png)](demo.png)

*The v1.4.0 demo after the automatic preview: instrument cluster, scenario
brief, decision brief, compact telemetry array and linked charts. Values are a
preview run, not a real-time feed.*

## Live and local

| Surface | Entry point | Differences |
|---|---|---|
| Hosted | <https://cxy2696.github.io/opinionlab/> | No install; browser preview; CSV export; no server-side report or Ollama |
| Local full service | `make demo` -> <http://127.0.0.1:8000/api/v1/demo/app> | Real engine; full scenario library; offline HTML report; interactive API docs at <http://127.0.0.1:8000/docs> |
| Single-container demo | `make demo-container` | Real engine and reports without PostgreSQL, Redis or MinIO |

```bash
make setup
make demo
# http://127.0.0.1:8000 -> /api/v1/demo/app
```

`make setup` creates a local `.env` from [`.env.example`](../.env.example) if
needed and, when Docker is available, starts PostgreSQL, Redis and MinIO and
runs the migrations. The hosted page uploads nothing. The local full service
uses the engine, serves reports and can opt into local Ollama. The
single-container demo runs the same public API without the database-backed
surfaces.

## First 30 seconds

The page does not wait for a click: it runs the selected scenario's default
parameters once as a **preview** and populates every panel. The hero footer says
`PREVIEW // n REPLICAS`; pressing **Run simulation** re-runs with the current
controls and changes the label to `LIVE RUN`.

| Query parameter | Effect |
|---|---|
| `?template=S7` | Open a specific template |
| `?q=1.8&mu=3&steps=120&repeats=8&seed=42` | Pre-fill controls |
| `?lang=en|zh|ja|de` | Select the UI language |
| `?run=1` | Run once after load instead of only previewing |
| `?autorun=0` | Disable the automatic preview (useful for screenshots) |

A preview is never used as the comparison baseline. The first real run has no
"previous" run; the second real run enables **Compare**.

## Interface tour

| Area | What it shows | How it is computed |
|---|---|---|
| **Cohesion gauge** | Final agreement | `100 x (1 - mean diversity_final)` across replicas |
| **Peak-turn gauge** | Largest single-step switch | `100 x max(cascade)` of the displayed run |
| **3D stage** | Decorative 150-node projection | Not a data-accurate network plot |
| **Replicas** | Independent runs behind the estimate | `n` of `diversity_final` |
| **Mean majority** | Mean step to an 80% majority | Replicas that reached a majority; censored replicas excluded |
| **Peak at step** | Where the largest burst happened | Argmax of the displayed run's cascade |
| **95% confidence** | Half-width of the final-diversity interval | `(ci95_hi - ci95_lo) / 2` |

Below the hero:

- **Control deck:** scenario, question, `q`, latency, steps, replicas, seed,
  presets, the run button, the demo caps and the parameter guide.
- **Results head:** verdict, summary, the "how to read" line and the run-quality
  strip (engine, graph size, replicas, censored replicas, underpowered flag,
  engine warnings, preview label).
- **Scenario brief:** where this scenario is actually used, which parameters to
  set first, the signal to watch, and collapsible assumptions and limits. The
  text comes from the scenario YAML, so the numbers and their caveats travel
  together.
- **Decision brief:** what the run informs, timing nodes (take-off, peak,
  majority, this run's intervention), a simulated action window, follow-up
  checks and the fixed caveat.
- **3D telemetry array:** opinion terrain, cascade bars and stance cloud in a
  compact row on desktop, with live peak/current stats and hover readouts.
- **Charts:** diversity (this run, replica median, 10-90% band, timing markers
  and an optional previous-run overlay), opinion shares and cascade per step.
- **Replay:** play or scrub the series without recomputing.
- **Metrics:** diversity, cascade P99, majority step, stable-majority rate,
  entropy and polarization, each with its 95% interval, `n` and a plain-language
  reading.
- **Exports:** CSV in both surfaces, a single-file HTML report in the local
  service, and a parameter link.

Help buttons open a fixed-position tooltip that is not clipped by the scrollable
control rail. The rail itself scrolls independently on short screens; the run
button stays reachable.

### Parameter guide

The collapsible **How to set these knobs** table in the control rail explains,
for each knob, what happens when it is raised and what data to calibrate it
from. It complements the inline hints and the scenario-specific "set these
first" paragraph in the scenario brief.

### Run-quality strip

Every result carries evidence flags, separate from the metric estimates:

| Chip | Meaning |
|---|---|
| `ENGINE` | `sparse_vector` for the real engine; `browser-binary` for the hosted preview |
| nodes / edges | Graph size actually used |
| replicas | Number of independent runs |
| `censored` | Replicas with no majority inside the window; their consensus time is excluded, not set to zero |
| `underpowered` | `n < 30`; the interval is wider than a normal approximation and should not drive a decision alone |
| warnings | Engine warnings such as zero-denominator edges or all-zero weights |
| preview | The hosted page ran the lightweight browser simulator |

## Browser preview fidelity

The hosted page uses the same conformity map, latency clock, stochastic decision
rule and stable-majority definition as the Python reference kernel. A parity
test pins the conformity map to the Python implementation.

| Feature | Hosted preview | Full engine |
|---|---|---|
| Stances | Binary (K = 2) | 2-6 |
| Node weights | Uniform | Uniform, engagement, centrality or custom |
| Aggregation | Mean | Mean, `max`, `size_weighted` |
| Latency | Constant, normal, exponential or lognormal integer sweeps | Also continuous |
| Topology | Static | Static or time-varying |
| Shocks | No | `flip_share`, `edge_boost`, `new_opinion` |
| Interventions | One-shot debunk/seed/flip; boost/dampen bias | Full set, including weight shift |
| Engine | Browser JavaScript | CSR or event-driven Python |
| Export | CSV | CSV, Parquet, figure, manifest, single-file HTML report |

If a scenario needs something outside the preview column, use `make demo` or the
CLI. Multi-stance specs are supported by the engine and the scenario API, but
the no-login demo form exposes binary templates; use `hnle simulate` or a
scenario spec for `K > 2`. The UI labels the preview in the hero footer and the
quality strip.

## Reading the charts

| Chart | What to look for |
|---|---|
| Diversity | Solid line is this run; dashed line is the replica median; the band is 10-90%. A wide band means the result depends on randomness. Vertical markers show take-off, peak and majority. |
| Opinion shares | How the share of each stance changes; the stacked area shows which stance gains over time. |
| Cascade | Share of people changing in each step; spikes mark sudden shifts. Vertical markers match the diversity chart. |

- `n` is the number of replicas aggregated. Do not over-read intervals when
  `n < 30`.
- The majority step counts only replicas that reached a majority; if none did,
  the card says so. The censoring state is preserved rather than reported as
  zero.
- The confidence interval is a Student-*t* interval, not a normal
  approximation; see the [Math model](MATH_MODEL.md#6-monte-carlo-estimator-and-intervals).
- Bounded intervals are clamped to their feasible range **for display only**
  (for example, a diversity interval cannot show a negative lower bound). The
  underlying estimate is unchanged.

## Decision brief and timing

Each run reports:

1. What decision it can inform (for example, timing and strength of debunking).
2. Key timing nodes: cascade take-off, peak, majority and this run's
   intervention.
3. A simulated action window, for example "about two reaction cycles before the
   peak (steps 14-20)".
4. Follow-up checks: rerun with one timing change, compare CIs, raise replicas,
   calibrate on real data. When consensus already holds, a fourth check suggests
   changing `q` or latency to test whether the window moves.
5. A caveat: timing advice is a simulated window, not a forecast of real event
   timing.

The brief appears in the demo and in the local service's downloaded HTML report.

## API

The local service exposes the demo API at `/api/v1/demo`; interactive OpenAPI
docs are at `/docs`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/demo/templates` | Enabled templates, defaults, features, operator `limits` |
| POST | `/api/v1/demo/simulate` | One small Monte Carlo run: metrics, series, decision, quality |
| POST | `/api/v1/demo/report` | Single-file HTML report |
| POST | `/api/v1/demo/narrate` | Optional Ollama narration (off by default) |
| GET | `/api/v1/demo/echarts.js` | Local ECharts bundle |
| GET | `/api/v1/demo/app` | The demo page |

Service-level endpoints:

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Service liveness |
| GET | `/metrics` | Prometheus metrics |
| GET | `/docs` | Interactive OpenAPI documentation |

```bash
curl -s http://127.0.0.1:8000/api/v1/demo/simulate \
  -H 'Content-Type: application/json' \
  -d '{"template_key":"S2","q":1.8,"latency_mu":3,"repeats":8,"seed":42,"steps":120}'
```

The response has `metrics`, `series`, `summary`, `summary_text`, `decision`,
`quality`, `spec` and the fixed `disclaimer`. `time_to_consensus` is censored:
`n` counts only replicas that reached a majority and `mean` is `null` if none
did. The [User guide](USER_GUIDE.md#api-cookbook) has the full shape and curl
examples.

## Ollama-assisted narration

The local full service can optionally call a local Ollama model to restate a run
and suggest two next experiments.

- Off by default: set `OLLAMA_ENABLED=true` and run
  `ollama serve && ollama pull llama3.2`.
- It reads engine numbers only; it computes no metrics, predicts no individuals
  and does not decide.
- Output is labelled "AI-assisted explanation, not a conclusion".
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
| `DEMO_MAX_STEPS` | 200 | Step cap; the UI reads it from `/templates` |
| `DEMO_MAX_REPEATS` | 20 | Replica cap; the UI reads it from `/templates` |
| `DEMO_MIN_STEPS` / `DEMO_MIN_REPEATS` | 10 / 1 | Lower bounds echoed to the browser |
| Rate limits | 100 global / 20 IP / 30 user / 200 org rps | Shared token buckets |
| Observability | `/metrics` | API latency, queue depth, replica failures |

- The public endpoints do not require login and do not write to the database.
- The four-language UI covers the on-screen controls, scenario questions and
  interpretations, chart labels, metrics, summaries and decision briefs. The
  newer scenario-brief fields are authored in English and Chinese; Japanese and
  German fall back to a localized generic guide for those three rows.
  Optional Ollama narration follows the selected language; the downloadable HTML
  report remains bilingual English/Chinese.
- Change caps in `.env` and restart the API; the browser picks them up on the
  next page load.
- **Asset ownership:** `apps/web/index.html`, `apps/web/app.js` and the files in
  `apps/web/` are the source. `scripts/build_site.py` generates
  `site/index.html`, `site/app.js` and `site/templates.json`, and copies
  `style.css`, `scene.js`, `galaxy.js`, `field3d.js`, `particles.js`, `i18n.js`
  and `sim.js`. `site/echarts.min.js` is decompressed from the engine package.
  Do not edit `site/app.js` or `site/index.html` by hand; run `make site`.
- The local page is served from [`apps/web/`](../apps/web/); the demo API is in
  [`apps/api/app/demo.py`](../apps/api/app/demo.py).

## Use cases and related reading

- Early what-if exploration for policy and communications teams.
- Quick sensitivity checks for researchers.
- Reviewing group metrics, confidence intervals and disclaimers in a browser.
- Comparing timing options before a communication or moderation window.

See the [User guide](USER_GUIDE.md) for the full path, [Use cases](USE_CASES.md)
for the questions, [Model card](MODEL_CARD.md) for the product boundary, and
[Architecture](ARCHITECTURE.md) for the data flow behind the interface.
