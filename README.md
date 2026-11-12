# OpinionLab

[![CI](https://github.com/cxy2696/opinionlab/actions/workflows/ci.yml/badge.svg)](https://github.com/cxy2696/opinionlab/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](pyproject.toml)
[![Version: 1.4.0](https://img.shields.io/badge/version-1.4.0-22d3ee.svg)](CHANGELOG.md)

OpinionLab is a scenario engine for group opinion dynamics. You describe a
population, a group structure, a conformity strength and a reaction-time
distribution; it runs many independent replicas, reports a range instead of a
single number, and writes a run that can be inspected, replayed and shared.

It is the engineering counterpart to the
[HNL research repository](https://github.com/cxy2696/Hypergraph-Nonlinear-Latency-Voter-Model).
That repository contains the paper, the formal binary model, the proofs and the
reproduction package. OpinionLab contains a broader engine, a service layer,
scenario templates, reports and a browser UI. The two share the binary
conformity kernel, but OpinionLab is not a reproduction of the paper and its
numbers should not be compared with the paper's numbers. The boundary is
documented in [`docs/MATH_MODEL.md`](docs/MATH_MODEL.md) and in the research
repository's [`docs/RELATIONSHIP.md`](https://github.com/cxy2696/Hypergraph-Nonlinear-Latency-Voter-Model/blob/main/docs/RELATIONSHIP.md).

**Live demo:** <https://cxy2696.github.io/opinionlab/><br>
**Latest release:** [v1.4.0](CHANGELOG.md) · **Start here:** [User guide](docs/USER_GUIDE.md) · **Docs:** [docs/README.md](docs/README.md)

[![OpinionLab instrument-cluster demo](docs/demo.png)](docs/DEMO.md)

*The v1.4.0 demo: a preview run on load, a scenario brief, a decision brief, a
compact 3D telemetry array and linked charts. The UI defaults to English and
supports Chinese, Japanese and German.*

## What it does

A run starts from a `ModelSpec`: the number of stances, the hypergraph, node
weights, the conformity exponent `q`, the latency distribution, the decision
rule and the Monte Carlo size. The engine supports two kernels: a synchronous
CSR kernel and an event-driven kernel with integer latency. The service layer
adds ingestion, job queues, storage, reports and a public demo API.

The output is not a point forecast. Each metric is a mean over replicas with a
Student-*t* 95% interval, plus the assumptions, limitations and evidence flags
that apply to the run. A consensus time is **censored** when no majority forms
inside the observation window; the run keeps that state and the UI shows it
instead of treating "not reached" as zero.

Typical questions:

- When should a correction, warning or policy message be released?
- Does a discussion converge to a genuine consensus or get flattened into one voice?
- Does a moderation action reduce a cascade, or only move it elsewhere?
- How wide is the uncertainty around any of those answers?

The engine does not model individuals, recommender systems, media agenda,
prices or offline behaviour, and it does not predict real events. See
[Model card](docs/MODEL_CARD.md) and [Compliance](docs/COMPLIANCE.md).

## Quick start

| Route | Command | What you get |
|---|---|---|
| Hosted browser demo | <https://cxy2696.github.io/opinionlab/> | No install; a preview simulation runs in the browser; CSV export |
| Local full service | `make demo` after `make setup` | Real engine, offline HTML reports, optional local Ollama |
| CLI | `uv run hnle …` after `make setup` | Reproducible runs, sweeps, calibration, comparison and artifacts |
| Single-container demo | `make demo-container` | Real engine and reports without PostgreSQL, Redis or MinIO |

From a fresh checkout:

```bash
git clone https://github.com/cxy2696/opinionlab.git
cd opinionlab
make setup
make demo        # http://127.0.0.1:8000 -> /api/v1/demo/app
```

`make setup` copies `.env.example` to `.env` when needed, installs the locked
environment and, when Docker is available, starts PostgreSQL, Redis and MinIO
and applies migrations. The demo endpoints work without those services; the
authenticated service needs them.

The CLI runs the engine without the service:

```bash
uv run hnle simulate --spec scenarios/s2_rumor_debunk_timing.yaml --repeats 20
uv run hnle report --run-id <run_id> --runs-dir runs
```

`hnle report` rebuilds a run from its manifest and verifies that the curves
match. `uv run hnle templates` lists the scenario library. The complete command
and parameter reference is in the [User guide](docs/USER_GUIDE.md).

## What is new in v1.4.0

- **Clearer evidence.** Aggregate consensus time uses a censored Student-*t*
  interval; every demo result carries a `quality` block (censored replicas,
  underpowered run, engine warnings) and a fuller `spec` echo.
- **Clearer scenarios.** Every template now carries a decision statement, a
  real-world use example, parameter-calibration guidance and the signal to
  watch, in English and Chinese. The UI shows them in a scenario brief.
- **Clearer interface.** One client for the hosted and local pages, a preview
  run on load, six metric cards, a compact three-panel telemetry deck, a
  parameter guide, a previous-run overlay and an unclipped help tooltip.
- **Clearer deployment.** A single-container demo image for hosts that only
  need the demo and offline reports, alongside the full Compose stack,
  Kubernetes values and air-gapped guide.
- **No front-end drift.** `site/index.html`, `site/app.js` and
  `site/templates.json` are generated from `apps/web/` and the scenario library;
  a test fails if the committed Pages artifact differs from the source.

The full list, including fixes and compatibility notes, is in
[CHANGELOG.md](CHANGELOG.md).

## The three surfaces

| Surface | Engine | Best for | Export |
|---|---|---|---|
| Hosted GitHub Pages demo | Lightweight browser preview: binary stances, uniform weights, mean aggregation | A first look, a quick sensitivity check | CSV |
| Local full service | Real Python engine through the FastAPI demo API | Reports, the full scenario library, optional Ollama narration; multi-stance specs via the CLI or scenario API | Single-file HTML report, CSV |
| CLI | Real Python engine, no server | Reproducible runs, sweeps, calibration, A/B comparison, manifest verification | Run directory with manifest, CSV, Parquet, figure, HTML |

The hosted preview uses the same conformity map, latency clock, stochastic
decision rule and stable-majority definition as the Python kernel. It does not
implement multi-stance runs, time-varying topology, engagement weights, shocks
or continuous latency; the UI labels it as a preview and the full engine is one
command away.

## Scenario library

The library has 16 templates: 15 enabled, plus a gated election-research
template. Each one is a complete `ModelSpec` plus graph and a question, a
decision, a real-world use, assumptions, limitations and the signal to watch.

| Group | Templates |
|---|---|
| Public communication | S1 policy release cadence, S2 rumor debunk timing, S3 platform governance, G6 disaster warning |
| Community and organization | S7 community consensus, S8 organizational change, G7 corporate change |
| Market and launch | S4 brand/KOL mix, S5 emergency science literacy, S6 financial expectations, S9 product launch |
| Research and reproduction | G1 academic reproduction, G2 fact checking, G3 public health, G4 platform systemic risk, G5 election research (gated) |

`uv run hnle templates` lists them with their questions. The
[User guide](docs/USER_GUIDE.md#scenario-library) has the decision, typical user
and signal for each one; the [Use cases](docs/USE_CASES.md) show worked
commands.

## How to read a result

1. **Start with the interval, not the mean.** The mean is an estimate over
   replicas; the 95% interval is the uncertainty. Overlapping intervals do not
   establish a difference.
2. **Check `n` and the quality flags.** Below 30 replicas the interval is
   underpowered. Censored replicas are reported separately; they are not zero.
3. **Read diversity with entropy and polarization, not alone.** Diversity is
   `1 - largest share`; entropy is more sensitive to a surviving minority, and
   polarization is a normalized dispersion index.
4. **Separate the burst from the end state.** A large cascade P99 can coexist
   with a fragmented, low-consensus end state. Watch the peak step and the final
   distribution together.
5. **Keep the assumptions with the numbers.** The scenario brief and the fixed
   disclaimer travel with every report; a result without them is not a
   deliverable.

The metric dictionary, censoring rules and multiple-comparison cautions are in
the [User guide](docs/USER_GUIDE.md#metric-dictionary) and
[Math model](docs/MATH_MODEL.md).

## A real-data case

The repository includes a small CC0 sample from the Kaggle *Social Media
Sentiments Analysis Dataset* and a worked case that ingests it, builds a
hashtag hypergraph and runs the engine:

```bash
make case
```

The raw sample has 732 posts from 670 user handles. After the valence filter,
the model graph has 586 users and 149 hashtag hyperedges. It forms 239
connected components; the largest holds 14% of the users. With `q=1.5`, a fixed
five-sweep latency and 30 replicates, the final diversity is 0.293 (95% CI
0.285-0.301) and the final majority is 0.744. Every component freezes, but no
run reaches an 80% population majority. That is the fragmentation result, not an
engine failure. The full output, commands and caveats are in
[`docs/CASE_STUDY.md`](docs/CASE_STUDY.md); the source data and hash are
documented in [`data/README.md`](data/README.md).

## Deployment

| Mode | Command | Needs |
|---|---|---|
| Local development | `make demo` | Python 3.12 and `uv`; Docker only for the authenticated service |
| Full Compose stack | `docker compose up -d --build` | PostgreSQL, Redis and MinIO containers; see [Runbook](docs/RUNBOOK.md) |
| Single-container demo | `make demo-container` | Docker only; real engine and reports, no database, no auth |
| Kubernetes | Helm values in [`deploy/k8s/`](deploy/k8s) | Pinned image digest, secrets, ingress; see [Air-gapped delivery](deploy/private/OFFLINE.md) |

The full stack exposes `/health`, `/metrics` and `/docs`. The demo container
exposes the same public demo API and the offline report endpoint; auth,
persisted runs, quotas and the worker queue are intentionally unavailable there.
Operator caps such as `DEMO_MAX_NODES`, `DEMO_MAX_STEPS` and
`DEMO_MAX_REPEATS` are echoed by `/api/v1/demo/templates` so the browser respects
them.

## Repository map

| Path | What it is |
|---|---|
| `packages/hnle/` | Standalone engine: model, hypergraph, CSR and event kernels, metrics, Monte Carlo, reports |
| `apps/api/` | FastAPI service: auth, quotas, jobs, connectors, compliance, demo API |
| `apps/web/` | The one web client: HTML shell, CSS, JavaScript, 3D scenes |
| `site/` | Generated GitHub Pages artifact; do not edit `site/app.js` or `site/index.html` by hand |
| `scenarios/` | 16 scenario templates (15 enabled; G5 gated) and valence mappings |
| `data/` | Fixed CC0 sample used by the real-data case |
| `examples/` | Minimal scripts plus the real-data case |
| `tests/` | Unit, integration, golden, front-end and documentation tests |
| `conformance/` | Shared binary fixture checked by this repository and HNL |
| `docs/` | User guide, mathematics, conformance, architecture, compliance, runbook, demo notes and screenshots |
| `benchmarks/` | Capacity benchmarks and Locust load scripts |
| `deploy/` | Compose, a single-container demo, Helm values for CN/global and air-gapped delivery |
| `migrations/` | Alembic database migrations |

`site/` is assembled by `make site` (or
[`scripts/build_site.py`](scripts/build_site.py)) from `apps/web/` and the
scenario library. The tracked files in `site/` are the build output; tests fail
when they drift. `runs/`, `datasets/` and downloaded reports are local and not
committed.

## Mathematics and conformance

The normative description is [`docs/MATH_MODEL.md`](docs/MATH_MODEL.md). It
states the conformity map, the aggregation rules, the latency clock, the
decision rules, the Monte Carlo estimator and the failure boundaries. The
formula-to-code map is in [`docs/CONFORMANCE.md`](docs/CONFORMANCE.md).

The shared part of the model with the HNL research repository is checked with a
small numerical fixture, [`conformance/binary_case.json`](conformance/binary_case.json).
The same file is checked by both repositories, so a drift in the shared kernel
fails in both. The fixture is not a snapshot of a simulation; its expected
values are computed from the equations.

## Tests and benchmarks

```bash
make check   # ruff, strict mypy, pytest
make bench   # capacity benchmark
make site    # regenerate the GitHub Pages artifact
make case    # ingest the CC0 sample and run the worked case
uv run pip-audit  # audit the locked dependency set
```

CI runs the checks on Python 3.12 with PostgreSQL and Redis services, runs the
migrations, and runs the capacity benchmark. The test suite covers the engine,
the API, the demo, the browser/Python conformity parity, the generated Pages
artifact, the documentation and the golden baselines. Some integration tests
are skipped locally when the services are not available; they run in CI.
Benchmark method, calibration and load scenarios are in
[`docs/capacity-report.md`](docs/capacity-report.md).

## Documentation

| Document | Contents |
|---|---|
| [User guide](docs/USER_GUIDE.md) | End-to-end usage, parameter reference, metric dictionary, cookbooks, deployment, FAQ |
| [Docs index](docs/README.md) | Reading paths and the full document list |
| [Use cases](docs/USE_CASES.md) | Worked questions, commands and interpretation |
| [Demo](docs/DEMO.md) | Hosted and local interfaces, four-language UI, API, limits |
| [Architecture](docs/ARCHITECTURE.md) | Layers, data flow, module map and generated asset pipeline |
| [Math model](docs/MATH_MODEL.md) | Formulas, `q` limits, estimators, censoring and failure boundaries |
| [Conformance](docs/CONFORMANCE.md) | Formula-to-code map and the shared fixture |
| [Case study](docs/CASE_STUDY.md) | A published hashtag sample, end to end |
| [Model card](docs/MODEL_CARD.md) | Capabilities, limits, prohibited uses |
| [Compliance](docs/COMPLIANCE.md) | Regions, review, deletion, red lines |
| [Runbook](docs/RUNBOOK.md) | Metrics, logs, rollback, tainted runs |
| [Capacity](docs/capacity-report.md) | Formula, calibration, load scenarios |
| [Data sample](data/README.md) | Kaggle source, hash, included-file limits |
| [Examples](examples/README.md) | Runnable examples and the real-data case |
| [Air-gapped delivery](deploy/private/OFFLINE.md) | Offline installation, verification and rollback |
| [Changelog](CHANGELOG.md) | Behaviour changes, UI releases and known deviations |

## Limits

- It does not predict individuals, profile people, or score real accounts.
- It does not model recommender systems, media agenda, offline behaviour or
  prices.
- Without external calibration, `q`, latency and initial stances are
  assumptions, and the conclusions are directional.
- Population-level `absorbing` and `runaway` labels assume a connected graph. On
  a fragmented graph, components can freeze while the population flag stays
  false; inspect the component structure.
- The hosted browser preview is deliberately narrower than the engine:
  binary stances, uniform weights, mean aggregation and no time-varying
  topology. Use the local service or CLI when those matter.

## License

MIT. The engine is in `packages/hnle/`; the service and UI are separate
applications. The research paper and the binary reference model are in the
[HNL repository](https://github.com/cxy2696/Hypergraph-Nonlinear-Latency-Voter-Model).
