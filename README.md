# OpinionLab

[![CI](https://github.com/cxy2696/opinionlab/actions/workflows/ci.yml/badge.svg)](https://github.com/cxy2696/opinionlab/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](pyproject.toml)

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

**Live demo:** <https://cxy2696.github.io/opinionlab/>

![OpinionLab demo](docs/demo.png)

## Quick start

In the browser, with no installation:

```text
https://cxy2696.github.io/opinionlab/
```

Locally, with the full service:

```bash
git clone https://github.com/cxy2696/opinionlab.git
cd opinionlab
make demo        # http://127.0.0.1:8000
```

The CLI runs the engine without the service:

```bash
make setup
uv run hnle simulate --spec scenarios/s2_rumor_debunk_timing.yaml --repeats 20
uv run hnle report --run-id <run_id> --runs-dir runs
```

## What it does

A run starts from a `ModelSpec`: the number of stances, the hypergraph, node
weights, the conformity exponent `q`, the latency distribution, the decision
rule, and the Monte Carlo size. The engine supports two kernels: a synchronous
CSR kernel and an event-driven kernel with integer latency. The service layer
adds ingestion, job queues, storage, reports and a demo API.

The output is not a point forecast. Each metric is a mean over replicas with a
Student-*t* interval, plus the assumptions and limitations that apply to the
run. Consensus times are censored when no majority forms inside the window, and
the reports state the censoring rate.

The scenario library has 15 templates: public communication, community
discussion, organizational change, product launch, and research/reproduction.
The browser UI can display English or Chinese labels; the repository
documentation itself is English-only.

## Repository map

| Path | What it is |
|---|---|
| `packages/hnle/` | Standalone engine: model, hypergraph, CSR and event kernels, metrics, Monte Carlo, reports |
| `apps/api/` | FastAPI service: auth, quotas, jobs, connectors, compliance, demo API |
| `apps/web/` | Source for the local demo UI: HTML, CSS, JavaScript, 3D scenes |
| `site/` | GitHub Pages site; shared assets are copied at build time |
| `scenarios/` | 15 runnable scenario templates |
| `examples/` | Two minimal examples: debunk timing and community conformity |
| `tests/` | Unit, integration, golden, frontend and documentation tests |
| `docs/` | Mathematics, conformance, architecture, compliance, runbook and demo notes |
| `benchmarks/` | Capacity benchmarks and Locust load scripts |
| `deploy/` | Compose, Helm and air-gapped delivery |
| `migrations/` | Alembic database migrations |

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
```

CI runs the checks on Python 3.12 with PostgreSQL and Redis services, runs the
migrations, and runs the capacity benchmark. The test suite covers the engine,
the API, the demo, the documentation and the golden baselines. Some integration
tests are skipped locally when the services are not available; they run in CI.

## Documentation

| Document | Contents |
|---|---|
| [Docs index](docs/README.md) | reading paths |
| [Use cases](docs/USE_CASES.md) | six worked questions, commands and interpretation |
| [Demo](docs/DEMO.md) | hosted page, API, limits, Ollama narration |
| [Architecture](docs/ARCHITECTURE.md) | layers, data flow, module map |
| [Math model](docs/MATH_MODEL.md) | formulas, `q` limits, estimators and failure boundaries |
| [Conformance](docs/CONFORMANCE.md) | formula-to-code map and the shared fixture |
| [Model card](docs/MODEL_CARD.md) | capabilities, limits, prohibited uses |
| [Compliance](docs/COMPLIANCE.md) | regions, review, deletion, red lines |
| [Runbook](docs/RUNBOOK.md) | metrics, logs, rollback, tainted runs |
| [Capacity](docs/capacity-report.md) | formula, calibration, load scenarios |
| [Changelog](CHANGELOG.md) | behaviour changes and known deviations |

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
