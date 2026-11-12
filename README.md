# OpinionLab

[![CI](https://github.com/cxy2696/opinionlab/actions/workflows/ci.yml/badge.svg)](https://github.com/cxy2696/opinionlab/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](pyproject.toml)
[![Version: 1.3.1](https://img.shields.io/badge/version-1.3.1-22d3ee.svg)](CHANGELOG.md)

OpinionLab is a scenario engine for group opinion dynamics. You describe a
population, a group structure, a conformity parameter and a delay distribution;
it runs many replicas, reports a range rather than a single number, and writes a
run that can be inspected later.

It is the engineering counterpart to the
[HNL research repository](https://github.com/cxy2696/Hypergraph-Nonlinear-Latency-Voter-Model).
That repository contains the paper, the formal binary model, the proofs and the
reproduction package. OpinionLab contains a broader engine, a service layer,
scenario templates, reports and a browser demo. The two share the binary
conformity kernel, but OpinionLab is not a reproduction of the paper and its
numbers should not be compared with the paper's numbers. The boundary is
documented in [`docs/MATH_MODEL.md`](docs/MATH_MODEL.md) and in the research
repository's [`docs/RELATIONSHIP.md`](https://github.com/cxy2696/Hypergraph-Nonlinear-Latency-Voter-Model/blob/main/docs/RELATIONSHIP.md).

**Live demo:** <https://cxy2696.github.io/opinionlab/><br>
**Latest release:** [v1.3.1](CHANGELOG.md) · **Documentation:** [docs/README.md](docs/README.md)

[![OpinionLab instrument-cluster demo](docs/demo.png)](docs/DEMO.md)

*The v1.3.1 browser demo: a dashboard-style instrument cluster, live 3D opinion
stage, parameter controls and linked telemetry. The UI defaults to English and
supports Chinese, Japanese and German. See [Demo](docs/DEMO.md) for a guided
tour.*

## Quick start

| Route | Command | What you get |
|---|---|---|
| Hosted browser demo | <https://cxy2696.github.io/opinionlab/> | No install; a lightweight binary simulation runs in the browser |
| Local full service | `make demo` after `make setup` | Real engine, multiple stances, reports and interactive API docs |
| CLI | `uv run hnle …` after `make setup` | Reproducible engine runs and artifacts without a service |

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
match. The local demo's **Report** button generates a separate single-file HTML
report; the hosted demo exports CSV.

## What it does

A run starts from a `ModelSpec`: the number of stances, the hypergraph, node
weights, the conformity exponent `q`, the latency distribution, the decision
rule, and the Monte Carlo size. The engine supports two kernels: a synchronous
CSR kernel and an event-driven kernel with integer latency. The service layer
adds ingestion, job queues, storage, reports and a demo API.

The output is not a point forecast. Each metric is a mean over replicas with a
Student-*t* interval, plus the assumptions and limitations that apply to the
run. A consensus time is censored when no majority forms inside the observation
window; the run keeps that state, and the browser demo shows it instead of
treating "not reached" as zero.

The scenario library has 16 templates: 15 enabled, plus a gated election
template. The enabled set covers public communication, community discussion,
organizational change, product launch, and research/reproduction. The browser
UI defaults to English and can switch to Chinese, Japanese or German; the
repository documentation itself is English-only.

### Product surfaces

- **Hosted demo:** the GitHub Pages build in [`site/`](site/) runs a
  dependency-free binary simulator locally in the browser. Charts, the 3D
  telemetry array and the instrument-cluster gauges update after each run.
- **Local service:** [`apps/web/`](apps/web/) is served by the FastAPI demo API.
  It adds multi-stance runs, offline HTML reports and the optional local
  Ollama narration.
- **CLI:** [`packages/hnle/`](packages/hnle/) provides simulation, ingesting,
  calibration, sweeps, comparison and replay verification.

## Current release: v1.3.1

- The browser demo has a new dashboard-style product hero with cohesion and
  peak-turn gauges, a central 3D opinion stage and four linked readouts.
- The UI language selector defaults to English and now includes Chinese,
  Japanese and German; the choice is kept in the URL and local storage.
- Screenshots and all repository docs are refreshed against v1.3.1, and visible
  version labels in the UI, API and deployment values are aligned.
- The service dependencies and security baseline are refreshed; `pip-audit`
  reports no known vulnerabilities. The pinned NumPy/SciPy/pandas stack is
  unchanged, so the engine baselines remain comparable.
- Engine dynamics are unchanged from v1.3.0. The full history, including
  breaking changes, is in [`CHANGELOG.md`](CHANGELOG.md).

## A real-data case

The repository includes a small CC0 sample from the Kaggle *Social Media
Sentiments Analysis Dataset* and a worked case that ingests it, builds a
hashtag hypergraph and runs the engine:

```bash
make case
```

The raw sample has 732 posts from 670 user handles. After the valence filter,
the model graph has 586 users and 149 hashtag hyperedges. It forms 239
connected components; the largest holds 14 % of the users. With `q=1.5`, a
fixed five-sweep latency and 30 replicates, the final diversity is 0.293
(95 % CI 0.285–0.301) and the final majority is 0.744. Every component freezes,
but no run reaches an 80 % population majority. That is the fragmentation
result, not an engine failure. The full output, commands and caveats are in
[`docs/CASE_STUDY.md`](docs/CASE_STUDY.md); the source data and hash are
documented in [`data/README.md`](data/README.md).

## Repository map

| Path | What it is |
|---|---|
| `packages/hnle/` | Standalone engine: model, hypergraph, CSR and event kernels, metrics, Monte Carlo, reports |
| `apps/api/` | FastAPI service: auth, quotas, jobs, connectors, compliance, demo API |
| `apps/web/` | Source for the local demo UI: HTML, CSS, JavaScript, 3D scenes |
| `site/` | GitHub Pages shell; shared assets are copied at build time |
| `data/` | Fixed CC0 sample used by the real-data case |
| `scenarios/` | 16 scenario templates (15 enabled; G5 gated) and valence mappings |
| `examples/` | Two minimal examples plus the real-data case |
| `tests/` | Unit, integration, golden, frontend and documentation tests |
| `conformance/` | Shared binary fixture checked by this repository and HNL |
| `docs/` | Mathematics, conformance, architecture, compliance, runbook, demo notes and screenshots |
| `benchmarks/` | Capacity benchmarks and Locust load scripts |
| `deploy/` | Compose, Helm values for CN/global and air-gapped delivery |
| `migrations/` | Alembic database migrations |

`runs/` is local output and is not committed. `site/` is assembled from the
site-specific shell plus shared assets copied from `apps/web/` by `make site`;
the tracked files in `site/` are the shell, client code and scenario export.
`data/` is a fixed CC0 sample, and `scenarios/` contains the templates and the
valence mappings.

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
make site    # assemble the GitHub Pages artifact
make case    # ingest the CC0 sample and run the worked case
uv run pip-audit  # audit the locked dependency set
```

CI runs the checks on Python 3.12 with PostgreSQL and Redis services, runs the
migrations, and runs the capacity benchmark. The test suite covers the engine,
the API, the demo, the documentation and the golden baselines. Some integration
tests are skipped locally when the services are not available; they run in CI.
Benchmark method, calibration and load scenarios are in
[`docs/capacity-report.md`](docs/capacity-report.md).

## Documentation

| Document | Contents |
|---|---|
| [Docs index](docs/README.md) | Reading paths, product tour and the full document list |
| [Use cases](docs/USE_CASES.md) | Six worked questions, commands and interpretation |
| [Demo](docs/DEMO.md) | Hosted and local interfaces, four-language UI, API, limits |
| [Architecture](docs/ARCHITECTURE.md) | Layers, data flow, module map and asset pipeline |
| [Math model](docs/MATH_MODEL.md) | Formulas, `q` limits, estimators and failure boundaries |
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

## License

MIT. The engine is in `packages/hnle/`; the service and UI are separate
applications. The research paper and the binary reference model are in the
[HNL repository](https://github.com/cxy2696/Hypergraph-Nonlinear-Latency-Voter-Model).
