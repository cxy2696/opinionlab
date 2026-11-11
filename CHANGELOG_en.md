# Changelog

> **In one minute**
>
> - v1.0 upgrades the prototype: node-centric updates, explicit decision rules, deterministic RNG, manifests and CIs.
> - Results intentionally differ from the upstream prototype.
> - Known deviations and capacity coefficients are environment-dependent; recalibrate before release.

## v1.0.0 — 2026-11-11 (upgraded from the upstream research prototype)

### Behaviour changes

- Node-centric, order-independent updates (OPT-01); the prototype's hyperedge loop depended on
  iteration order.
- Explicit `decision_rule` (`stochastic`, `argmax`, `threshold`); the paper's deterministic argmax is
  now selectable rather than implicit.
- `SeedSequence` streams for init, latency and decisions; same spec + seed reproduces a run.
- Run `manifest` records spec hash, data hash, engine version and seed.
- 95% confidence intervals via Welford aggregation.
- Group-only outputs: per-node traces are rejected at the API boundary.

### Dependencies and infrastructure

- Python 3.12, `uv` workspace, pinned `click==8.1.7`.
- FastAPI + SQLAlchemy async + Postgres 16 (RLS, monthly partitions).
- Redis/Celery, structlog/Prometheus, Docker Compose and Helm (CN/global).
- GitHub Actions: check, migrate, bench, weekly security audit.

### Known deviations

- The prototype is order-dependent and uses global random state; V1 deliberately changes results.
- The stochastic rule differs from the paper's deterministic argmax; reports state which rule was used.
- Capacity coefficient `c` is host-dependent; recalibrate with `make bench`.
