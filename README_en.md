# OpinionLab · Scenario Sandbox

[![CI](https://github.com/cxy2696/opinionlab/actions/workflows/ci.yml/badge.svg)](https://github.com/cxy2696/opinionlab/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](pyproject.toml)

[中文](README_cn.md) · **English** · [Language landing](README.md)

**Turn “how would this group react?” into an experiment you can repeat.**
Not a fortune teller — a sandbox for trying “what if” before you publish, announce or intervene.

**Live demo:** https://cxy2696.github.io/opinionlab/

![OpinionLab demo](docs/demo.png)

![3D telemetry array](docs/telemetry-3d.png)

*① opinion terrain ② cascade bars ③ stance cloud*

## The problem

A message goes out. Some people share it immediately, others react two days later. Small groups
reinforce each other; large groups drown out minorities. Communications, community and policy teams
usually can only “publish and see”.

OpinionLab turns this into an experiment: vary conformity, latency and intervention timing, then watch
how the group evolves. The output is a **range with 95% confidence intervals**, plus a plain-language
statement of what the result can and cannot support.

## What you can do

| Setting | Question | Template |
|---|---|---|
| Crisis communication | Does debunking two days earlier change the negative share? | S2 |
| Community discussion | Is the group converging, or being pushed into a silent majority? | S7 |
| Organizational change | When does sentiment rebound after staged announcements? | S8 |
| Product launch | Is early buzz the same as durable word of mouth? | S9 |
| Policy / platform governance | Where should the intervention window sit? | S1 / S3 |
| Teaching and research | How does `q` change consensus? What is the classical limit? | G1 |

Configuration, commands and reading guides are in [`docs/USE_CASES_en.md`](docs/USE_CASES_en.md).

## Quick start

**In the browser** (no install): https://cxy2696.github.io/opinionlab/

**Locally** (full service):

```bash
git clone https://github.com/cxy2696/opinionlab.git
cd opinionlab
make demo        # http://127.0.0.1:8000
```

Pick a template, drag `q`, and run. The page shows diversity, confidence intervals, a decision brief
and the 3D telemetry array.

**CLI:**

```bash
make setup
uv run hnle simulate --spec scenarios/s2_rumor_debunk_timing.yaml --repeats 20
uv run hnle report --run-id <run_id> --runs-dir runs
```

## What is in the UI

- **3D industrial tracker:** rotating opinion network, target lock, scan sweep and live telemetry.
- **3D telemetry array:** opinion terrain, cascade bars and stance cloud, with peak/current readouts,
  legends and hover values on the bars.
- **Explained parameters:** every knob has “what it is / why it matters”, hover tips and presets
  (quick look, steady estimate, high conformity, slow reaction).
- **Decision brief:** what the run informs, timing nodes (take-off/peak/majority/intervention), a
  simulated window and follow-up checks.
- **Chinese/English switch** for templates, charts, summaries and decisions.
- **Optional local Ollama narration:** off by default; restates results and suggests next experiments
  without computing metrics or replacing conclusions.

## Three concrete cases

1. **Does debunk timing matter?**
   ```bash
   uv run python examples/rumor_timing.py --repeats 8
   ```
   Compare final positive share at T+2 / T+12 / T+24. If the CIs overlap, do not claim “earlier is
   better” under these assumptions.

2. **Could a community be pushed into silence?**
   ```bash
   uv run python examples/community_consensus.py --repeats 6
   ```
   Raise `q` from 1.0 to 2.4. Ideally consensus speeds up without diversity collapsing to zero.

3. **Academic reproduction**
   ```bash
   uv run hnle simulate --spec scenarios/g1_academic_reproduction.yaml --repeats 20
   ```
   At `q=1`, binary hyperedges and unit latency, inspect consensus probability as group size grows.

## Repository map

| Path | What it is |
|---|---|
| `packages/hnle/` | Standalone engine: model, hypergraph, two kernels, metrics, Monte Carlo, reports; no database |
| `apps/api/` | FastAPI service: auth/RBAC, quotas, jobs, connectors, compliance, demo API |
| `apps/web/` | Source for the local demo UI: HTML/CSS/JS, 3D scenes, particles, galaxy |
| `site/` | GitHub Pages site; only site-specific files, shared assets copied at build time |
| `scenarios/` | 15 bilingual scenario templates, directly runnable |
| `examples/` | Two minimal examples: debunk timing and community conformity |
| `tests/` | Unit, integration, golden, frontend and documentation tests |
| `docs/` | Paired Chinese/English math, architecture, compliance, runbook and demo docs |
| `benchmarks/` | Capacity benchmarks and Locust load scripts |
| `deploy/` | Compose, Helm (CN/global) and air-gapped delivery |
| `scripts/` | Static-site assembly and scenario export |
| `migrations/` | Alembic database migrations |

## Rigour and reproducibility

The formal model, weighted edge map, `q` limits, latency semantics, Monte Carlo estimator and CI
assumptions are documented in [`docs/MATH_MODEL_en.md`](docs/MATH_MODEL_en.md). Each formula maps to a
specific function, and the doc states where conclusions are directional only. For a plain-language
summary, read [`docs/MODEL_CARD_en.md`](docs/MODEL_CARD_en.md).

## Templates (15)

- **S1–S6 public communication:** policy cadence, debunk timing, platform governance, brand/KOL,
  health literacy, financial expectations.
- **S7–S9 general use:** community consensus, organizational change, product launch.
- **G1–G7 research/verification:** academic reproduction, fact-checking, public health, platform risk,
  disaster warning, corporate change. G5 election templates are disabled by default and require
  use-case approval.

## Documentation

| Document | Contents |
|---|---|
| [Docs index](docs/README_en.md) | reading paths by role |
| [Use cases](docs/USE_CASES_en.md) | six real questions, commands and interpretation |
| [Demo](docs/DEMO_en.md) | hosted page, APIs, limits, Ollama |
| [Architecture](docs/ARCHITECTURE_en.md) | layers, data flow, invariants |
| [Math model](docs/MATH_MODEL_en.md) | formulas, `q` limits, estimators and failure boundaries |
| [Model card](docs/MODEL_CARD_en.md) | capabilities, limits, prohibited uses |
| [Compliance](docs/COMPLIANCE_en.md) | regions, review, deletion, red lines |
| [Runbook](docs/RUNBOOK_en.md) | metrics, logs, rollback, tainted runs |
| [Capacity](docs/capacity-report_en.md) | formula, calibration, load scenarios |
| [Changelog](CHANGELOG_en.md) | behaviour changes and known deviations |

## Tests and benchmarks

```bash
make check   # ruff + mypy --strict + pytest
make bench   # 100k-node benchmark, fails above 90s
make site    # assemble the GitHub Pages artifact
```

- 220+ tests cover engine, API, demo, docs and golden baselines.
- Postgres/Redis integration uses CI services; set `TEST_DATABASE_URL` locally.
- Shared frontend assets live only in `apps/web/` and are copied into `site/` at build time.

## Deployment

- Single host: `docker-compose.yml` (db / redis / minio / api / worker).
- Cluster: `deploy/k8s/helm-cn` and `helm-global`.
- Air-gapped: [`deploy/private/OFFLINE_en.md`](deploy/private/OFFLINE_en.md).

## Boundaries

- No individual prediction, profiling or scoring.
- Does not model recommender systems, media agenda, offline behaviour or real prices.
- Without calibration, conclusions are directional; assumptions, limitations and the disclaimer stay
  in every report.

## License

MIT
