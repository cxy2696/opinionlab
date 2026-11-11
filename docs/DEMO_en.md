# Demo application

OpinionLab includes a no-login browser sandbox for the full loop: choose a scenario, tune parameters,
watch the group evolve and download a report.

## Live and local

- Hosted (no install, runs in the browser): **https://cxy2696.github.io/opinionlab/**
- Full service locally:

```bash
make demo
# http://127.0.0.1:8000 -> /api/v1/demo/app
```

The hosted page computes locally with a lightweight binary simulator and uploads nothing. The local
service uses the real engine, supports multiple opinions, interventions and reports.

## Features

- 15 bilingual scenario templates with the question they help answer.
- Inline explanations for every parameter, hover tips and one-click presets.
- Three linked charts with particle overlays: diversity flow, drifting opinion particles and cascade bursts.
- A cockpit shell with a system status bar, numbered decks, UTC clock, telemetry and responsive layouts for desktop, tablet and phone.
- A decision brief: what the run informs, key timing nodes, a simulated window, follow-up checks.
- Replay, comparison with the previous run, CSV export and shareable parameter links.
- A 3D industrial tracker shows the opinion network with lock brackets and telemetry.

## How to read the charts

| Chart | What to look for |
|---|---|
| Diversity | Solid line is this run; dashed line is the replica median; the band is 10–90%. A wide band means the result depends on randomness. |
| Opinion shares | How the share of each stance changes; the stacked area shows who is winning over time. |
| Cascade | Share of people changing in each step; spikes mark sudden shifts. |

- `n` is the number of replicas aggregated. Do not over-read intervals when `n < 30`.
- The consensus step counts only replicas that reached a majority; if none did, the card says so.

## Decision brief and timing

Each run reports:

1. What decision it can inform (for example, timing and strength of debunking).
2. Key timing nodes: cascade take-off, peak, majority and this run's intervention.
3. A simulated action window, for example “about two reaction cycles before the peak (steps 14–20)”.
4. Follow-up checks: rerun with one timing change, compare CIs, raise replicas, calibrate on real data.
5. A caveat: timing advice is a simulated window, not a forecast of real event timing.

The brief appears in the demo and in the downloaded HTML report.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/demo/templates` | enabled templates and defaults |
| POST | `/api/v1/demo/simulate` | one small Monte Carlo run, metrics and series |
| POST | `/api/v1/demo/report` | single-file HTML report |
| GET | `/api/v1/demo/echarts.js` | local ECharts bundle |
| GET | `/api/v1/demo/app` | the demo page |

```bash
curl -s http://127.0.0.1:8000/api/v1/demo/simulate \
  -H 'Content-Type: application/json' \
  -d '{"template_key":"S2","q":1.8,"latency_mu":3,"repeats":8,"seed":42,"steps":120}'
```

## Ollama-assisted narration

The local full service can optionally call a local Ollama model to restate a run and suggest two
next experiments.

- Off by default: set `OLLAMA_ENABLED=true` and run `ollama serve && ollama pull llama3.2`
- It reads engine numbers only; it computes no metrics, predicts no individuals and does not decide
- Output is labelled “AI-assisted explanation, not a conclusion”
- The hosted demo cannot call local Ollama; the button explains this

```bash
ollama serve
ollama pull llama3.2
OLLAMA_ENABLED=true make demo
```

## Limits and operations

| Item | Default | Notes |
|---|---|---|
| `DEMO_MAX_NODES` | 400 | node cap for the public demo |
| `DEMO_MAX_STEPS` | 200 | step cap |
| `DEMO_MAX_REPEATS` | 20 | replica cap |
| Rate limits | 100 global / 20 IP / 30 user / 200 org rps | shared token buckets |
| Observability | `/metrics` | API latency, queue depth, replica failures |

- The public endpoints do not require login and do not write to the database.
- Change caps in `.env` and restart the API.
- Static assets are split into `index.html`, `style.css`, `app.js`, `scene.js` and `i18n.js` for
  maintainability; the ECharts bundle is served locally, not from a CDN.

## Use cases

- Early what-if exploration for policy and communications teams.
- Quick sensitivity checks for researchers.
- Reviewing group metrics, confidence intervals and disclaimers in a browser.
