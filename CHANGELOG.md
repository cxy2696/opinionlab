# Changelog

**Related:** [Repository README](README.md) · [Docs index](docs/README.md)

## v1.4.0 — 2026-11-13

### Playback and 3D deck fixes

- Replay now uses a time-based `requestAnimationFrame` loop instead of a
  70 ms `setInterval`. A fast chart path replaces only the point arrays, keeps
  the axes and legend fixed, and skips ECharts enter/update animation, so a
  100-step run plays at a steady ~30 fps instead of ~10 fps. The loop derives
  the step from elapsed time and skips rather than queues if a device is slow.
- The 3D telemetry deck repaints when data changes under
  `prefers-reduced-motion`, so scrub/replay and hover work in that mode.
  Cascade bars keep their current height between data updates instead of
  collapsing on every replay frame, and the bar hit area is positioned on the
  bar body rather than its tip.
- Decorative canvas overlays are throttled to ~30 fps (12 fps during playback),
  the drawing load is reduced while playing, and particle clouds are seeded
  once instead of being rebuilt on every step. This leaves the main thread to
  the charts and removes the replay jitter.
- Scrub updates are coalesced into one animation frame and playback stops
  cleanly on a new run, a scrub, or Escape.

### Engine and API rigour

- Aggregate `time_to_consensus` now uses a Student-*t* interval over the
  replicas that actually reached a majority (`hnle.mc.censored_interval`), with
  `n` counting the uncensored replicas and `null` when none did. The previous
  demo endpoint used a normal approximation and a different code path from the
  rest of the estimator.
- Fixed a decision-brief bug that truncated the fourth, goal-dependent
  follow-up ("if the goal is to delay consensus...") even when consensus had
  formed. The brief now keeps it only in that state.
- `init_mode: fixed_ratio` now supports `n_opinions > 2`: stance 1 receives the
  target share and the remainder is split as evenly as possible across the other
  stances. The binary branch keeps its historical draw order, so seeded
  baselines remain reproducible.
- Demo results now carry a `quality` block (engine, graph size, replicas,
  censored replicas and rate, underpowered flag, streaming degradation and
  engine warnings) and a fuller `spec` echo (engine, latency distribution,
  opinion count and consensus threshold). The verdict uses the aggregate
  absorbing rate, not the first replica.
- `/api/v1/demo/templates` returns operator-configured `limits`, so the browser
  respects `DEMO_MAX_STEPS`, `DEMO_MAX_REPEATS`, `DEMO_MIN_STEPS` and
  `DEMO_MIN_REPEATS` instead of hard-coding the caps.
- Scenario templates are the source of the decision text. `Template` gained
  `decision`, `real_world`, `parameters` and `watch` fields in English and
  Chinese, and the demo API consumes them instead of a duplicated key map.
- `MetricName` now matches the exact keys emitted by `MetricSummary`
  (`absorbing`/`runaway` instead of the unused `absorbing_rate`/`runaway_rate`,
  plus the missing `avg_share_final`, `oscillation_sign_persistence` and
  `oscillating`). `ModelSpec.metrics` now actually filters the aggregate result
  instead of being ignored; the CLI and sweep report a clear message when a
  selected metric is excluded.
- The browser preview now uses the same conformity map, latency clock,
  stochastic decision rule and stable-majority definition as the Python kernel,
  and supports constant, normal, exponential and lognormal integer latency,
  `fixed_ratio` initialisation and one-shot interventions. Multi-stance,
  time-varying topology, engagement weights and shocks remain Python-only and
  are labelled as such.

### Web client and layout

- The hosted and local pages now share one HTML shell and one client
  (`apps/web/app.js`). `scripts/build_site.py` generates `site/index.html`,
  `site/app.js` and `site/templates.json`, and a test fails when the committed
  Pages artifact drifts from the source.
- The page runs a preview immediately on load, so charts, metrics, the decision
  brief and the hero instruments are populated instead of leaving large empty
  cards. `?run=1` forces a normal run, `?autorun=0` disables the preview, and a
  preview no longer becomes the comparison baseline.
- Added a scenario brief card with where the scenario is used, which parameters
  to set first, what signal to watch, and collapsible assumptions and limits.
  Added a parameter guide table (effect of raising, calibration source) inside
  the control rail.
- Replaced the duplicated hero readouts with replicas, mean majority step, peak
  step and the 95% confidence half-width. The 3D telemetry deck is a compact
  three-panel row on desktop instead of one oversized terrain panel.
- Metrics expanded from four to six cards (diversity, cascade P99, majority
  step, stable-majority rate, entropy, polarization), with bounded intervals
  clamped to their feasible range for display.
- Compare now toggles a previous-run overlay; the CSV and HTML-report actions
  are separate; help text uses a fixed-position tooltip that cannot be clipped
  by the scrollable rail; status, verdict, summary and quality messages are
  announced with `aria-live`; Enter runs and Escape stops playback.
- Tightened responsive rules at 1440, 1200, 768 and 390 px. The generated
  screenshots are refreshed from the new layout.

### Deployment

- Added `deploy/docker/demo.Dockerfile` and `docker-compose.demo.yml`: a
  single-container, non-root demo with the real engine and offline reports, no
  PostgreSQL, Redis or MinIO, plus a healthcheck. `make demo-container` starts
  it. The full Compose stack is unchanged.
- The demo container documents that auth, persisted runs, quotas and the worker
  queue are intentionally unavailable; use the full stack for those.

### Documentation

- Added [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md): installation, the three
  surfaces, a guided session, a parameter reference with calibration guidance,
  a metric dictionary, censoring and interval rules, the scenario library, CLI
  and API cookbooks, deployment, privacy, troubleshooting and a glossary.
- Rewrote the README project description, surface summary, repository map,
  scenario overview and documentation index; expanded the demo guide with the
  preview, quality strip, scenario brief and parameter guide, and added the
  real-world application and parameter guidance to the use cases.
- Updated the architecture, math model, model card, runbook and air-gap notes
  for the unified client, the demo container, the censored interval and the
  multi-stance initialisation rule.
- Aligned every visible version label and Helm tag to v1.4.0.

### Tests

- Added tests for the censored Student-t interval, the multi-stance
  `fixed_ratio` split, the fourth decision follow-up, the browser/Python
  conformity parity, the enriched template export, the demo `quality` and
  `limits` payloads, and source-to-Pages drift.

### Compatibility

- Engine dynamics for existing binary scenarios are unchanged; the golden
  baselines still pass.
- The hosted `site/app.js` is generated. Edit `apps/web/app.js` and run
  `make site`; do not edit `site/app.js` directly.
- The default browser preview uses at least 8 replicas (subject to the demo
  cap), so its first-run intervals are less degenerate than the previous
  three-replica template default.

## v1.3.1 — 2026-11-12

### Changed

- Removed the tracked `sensitivity.json`, a generated CLI artifact that is
  already covered by `.gitignore`.
- Corrected the scenario count: the library has 16 templates, 15 enabled and
  the G5 election template gated. The README, demo note, examples index and
  template-test docstring now agree.
- Added a source-versus-generated note to the README: `runs/` is local,
  `site/` is assembled from the site shell plus shared `apps/web/` assets, and
  `data/` is a fixed CC0 sample.

### Demo and documentation

- Redesigned the browser product hero as a dashboard-style instrument cluster:
  cohesion and peak-turn gauges, a central 3D opinion stage, four linked
  readouts and a live preview/run state. The existing cockpit controls, 3D
  telemetry and multilingual labels are unchanged.
- Refreshed the README, docs index, demo guide, use cases, architecture, model
  card, compliance, runbook, capacity report, data note, examples and air-gap
  guide for v1.3.1. Every page now links back to the docs index and changelog.
- Replaced `docs/demo.png` and `docs/telemetry-3d.png` with screenshots from the
  current instrument-cluster build.
- Aligned visible version labels in the demo (`BUILD V1.3.1`), FastAPI app
  metadata and Helm image values. Documented that the hosted demo exports CSV
  while the local service exports an HTML report.
- Added Chinese, Japanese and German UI translations alongside the default
  English interface. The selector now uses native language names, localizes its
  accessible label, is URL-addressable (`?lang=en|zh|ja|de`), persisted locally,
  synchronized across tabs, and carried into shared run links.
- Localized dates follow the selected locale; cockpit/status labels and 3D
  telemetry badges were also translated.
- Localized scenario names, questions and interpretations, chart legends,
  metric cards, plain-language readings, summaries and decision briefs for
  Japanese and German, including the decision timing/follow-up content.
- Added Japanese and German Ollama narration prompts and localized disclaimer
  text; the narration follows the selected UI language.
- Added English/Japanese/German screenshots (`docs/demo*.png`) and documentation
  for the language selector.
- Corrected documentation claims about censored consensus reporting, the
  3D-telemetry/CSV split and the tainted-run surface.

### Operations

- Added `.env.example` and made the Compose `env_file` optional, so
  `docker compose config` and local startup no longer require a pre-existing
  `.env`. `make setup` now bootstraps the file, starts the local services when
  Docker is available and applies migrations.
- Replaced the placeholder Docker base-image digest with the real
  `python:3.12.12-slim-bookworm` index digest, and made the worker wait for
  MinIO as well as PostgreSQL and Redis.
- Added `.dockerignore` so local secrets, virtualenvs and runtime artifacts are
  not sent to the Docker daemon.
- `make site` now regenerates `site/templates.json` from the scenario library,
  and the Pages workflow also runs (and regenerates the export) when shared
  `apps/web/` assets, scenarios or build scripts change. Tests compare the
  committed export with the library.
- Added deployment tests for the env sample, optional Compose config, worker
  readiness and Pages path triggers.
- CI, migration, benchmark and security jobs now run `uv lock --check` /
  `uv sync --locked`, so a stale lockfile fails instead of being silently
  re-resolved.

### Dependencies and security

- Upgraded the service stack to FastAPI 0.162.5, Starlette 1.10.0,
  Pydantic 2.14.3 and pydantic-settings 2.16.2, with matching typing updates.
- Replaced `python-jose`/`ecdsa` with PyJWT 2.15.1 for HS256 tokens, removed
  the old JWT import shim and raised the development default secret to 32+
  bytes. Production deployments must supply their own secret.
- Updated Jinja2 to 3.1.6 and PyArrow to 23.0.1; the pinned numeric stack
  (NumPy, SciPy, pandas) is unchanged so golden results remain comparable.
- Updated test tooling to pytest 9.2.0, pytest-asyncio 1.4.1,
  pytest-benchmark 5.3.1 and Hypothesis 6.170.15, and set the async fixture
  loop scope explicitly.
- `uv run pip-audit` now reports no known vulnerabilities. The weekly security
  workflow therefore runs against a clean dependency set.

### Unchanged

- Engine dynamics are unchanged from 1.3.0.

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
