# Changelog

## v1.3.0 — 2026-11-12

### Added

- A real-data case built on the CC0 Kaggle *Social Media Sentiments Analysis
  Dataset*: `data/kaggle_sentiment.csv`, a 169-label valence mapping, and
  `examples/kaggle_hashtag_case.py`. `make case` ingests 732 posts, builds 149
  hashtag hyperedges, and runs 30 replicas.
- `docs/CASE_STUDY.md` reports the result: 239 components, largest 14.2 %,
  final diversity 0.293 [0.285, 0.301], final majority 0.744, every component
  internally absorbed, no 80 % population majority. The case is framed as a
  structural scenario, not a forecast.
- `simulate --graph` accepts an ingested `.npz` graph, so the output of
  `hnle ingest` can be run without writing a new scenario graph.
- `connected_components()` in `hnle.graph`, used by the case and available to
  callers.
- `tests/test_case_study.py` checks the sample ingest and the `--graph` path.

### Changed

- `hnle ingest` exposes `--user-column`, `--hashtags-column`,
  `--sentiment-column`, `--engagement-column`, `--min-size`, `--max-size` and
  `--allow-content`, so a CSV with non-default headers can be used directly.
- Ingest stats report the post-merge hyperedge count, matching the graph the
  engine actually uses.
- Version metadata to 1.3.0. Engine dynamics are unchanged from 1.2.0.

## v1.2.0 — 2026-11-12

### Documentation

- Repository documentation is English-only. The `_cn` editions of the README,
  changelog and docs were removed; `_en` files were renamed to their plain
  names. The browser demo keeps its optional Chinese UI translation; that is a
  user-facing feature, not a second documentation set.
- Rewrote the README and the docs index in a plainer voice: what the engine
  does, what it does not claim, and how it relates to the research repository.
- Added `docs/CONFORMANCE.md`, mapping each formula to a function and a test.

### Conformance

- Added `conformance/binary_case.json`, the same three-case fixture stored in
  the HNL research repository.
- Added `tests/test_conformance.py`, which checks this repository's
  `edge_distributions` and `aggregate_node_probabilities` against the fixture.
  A drift in the shared binary kernel now fails in both repositories.

### Unchanged

- No engine behaviour changes from 1.1.0. The version bump is for the
  documentation restructuring and the conformance contract.

## v1.1.0 — 2026-11-12

### Corrected mathematics

- The `threshold` rule now keeps the current stance unless a strictly more likely stance reaches the
  threshold; ties keep the status quo. The previous implementation set the binary opinion from
  `p1 >= τ` alone and ignored the current opinion.
- `max` aggregation is renormalised row-wise. An element-wise maximum of distributions is not a
  distribution; the previous code could pass rows summing to more than one to the sampler.
- `zscore` weight normalisation was removed. It could produce negative weights, which make the
  weighted counts negative and the fractional power `q` undefined. Weights are documented as
  non-negative; a zero-total edge falls back to uniform with a warning.
- The event kernel now uses the same change-triggered clock as the CSR engine, weighted opinion
  counts (it previously counted nodes rather than weights), and per-sweep series. It is restricted
  to integer latency steps; continuous latency is handled by the CSR engine.
- The conformity map, row normalisation, ordinal mean opinion and consensus test live in the shared
  `core/kernel.py`; the three engines no longer duplicate these formulas.
- `engagement` and `centrality` weight sources are now consumed. Ingested weights are attached to the
  `Hypergraph` and used by the engine; `centrality` is the incidence degree. Previously both sources
  silently fell back to uniform weights.

### Behaviour changes (breaking)

- Threshold semantics changed as above; a run that switched to 1 at `p1 >= τ` may now keep its
  current stance.
- `weights.normalize = "zscore"` is rejected at validation time; use `none` or `max`.
- `engine = "event_driven"` with `latency.quantize = "continuous"` is rejected; use
  `engine = "sparse_vector"`.
- Duplicate hyperedges are merged and duplicate node ids inside an edge are rejected. The synthetic
  generator now samples **distinct** edges, so the voter-limit golden baseline changed.

### Tests and documentation

- Added tests for threshold status-quo, max renormalisation, integer event/CSR equivalence at
  `L = 2` and `L = 5`, weighted event counts, and binary-only controls.
- `docs/MATH_MODEL.md` rewritten: `q > 0`, non-negative weights, normalised `max`,
  explicit threshold semantics, integer event clocks, Student-*t* intervals, and the censoring
  meaning of `time_to_consensus = -1`.
- Regenerated `tests/golden/v1_baseline.json` for the distinct-edge generator; `pre_fix_baseline.json`
  is unchanged.

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
