# User guide

**Applies to:** OpinionLab v1.4.0 · [Docs index](README.md) · [Changelog](../CHANGELOG.md)

OpinionLab is a scenario engine for group opinion dynamics. You describe a
population, a group structure, a conformity strength and a reaction-time
distribution; the engine runs many independent replicas and reports a range
rather than one number.

The normative equations are in the [Math model](MATH_MODEL.md); this page is the
practical path from installation to interpretation.

## What a run is - and what it is not

A **run** is one validated `ModelSpec` plus a hypergraph and a seed, evaluated as
`repeats` independent Monte Carlo replicas. Each replica gets its own seed stream
for initial opinions, latencies and decisions. The engine returns group-level
series and per-metric means with 95% confidence intervals; a CLI run also writes
an immutable artifact with a manifest. Same spec and seed reproduce the curves.

It is a group-level "what if" under stated assumptions, a distribution over
replicas rather than a point estimate, and a reproducible artifact.

A run **is not**:

- A forecast of a real event, a real population or a real date.
- A model of individuals. No per-node opinion trace is returned or accepted at
  the API and report boundaries.
- A causal estimate. Changing a parameter and rerunning is a scenario
  comparison, not evidence that a real intervention would cause that change.
- A model of recommender systems, media agenda, offline behaviour or prices.

## Who this guide is for

Analysts pick a template, tune `q` and latency and read intervals. Researchers
reproduce runs and calibrate. Communications and policy teams compare timing
options and share a report. Engineers install, deploy, monitor and audit.

## Install and set up

| Requirement | Notes |
|---|---|
| Python 3.12 | `pyproject.toml` requires `>=3.12,<3.13`; 3.13 is not supported |
| `uv` | Resolves the workspace, lockfile and editable packages |
| `make` | Optional convenience target; the underlying `uv` commands work directly |
| Docker | Optional. Only the full service needs PostgreSQL, Redis and MinIO |

```bash
git clone https://github.com/cxy2696/opinionlab.git
cd opinionlab
make setup
make demo
```

Open <http://127.0.0.1:8000/api/v1/demo/app> (the root URL redirects there).
`make setup` copies `.env.example` to `.env` if needed, runs `uv sync`, and, when
Docker is available, starts PostgreSQL, Redis and MinIO and applies
`uv run alembic upgrade head`. Without Docker it prints a skip message and
continues.

Edit `.env` before sharing a host. Replace `POSTGRES_PASSWORD`, keep the password
in `DATABASE_URL` in sync, set a random `JWT_SECRET` of at least 32 bytes, replace
the MinIO credentials and never commit `.env`.

### The no-Docker path

The engine has no database or network dependency. These work after `make setup`
even when Docker is absent:

| Works without PostgreSQL, Redis and MinIO | Needs the service stack |
|---|---|
| `uv run hnle simulate`, `report`, `sweep`, `compare`, `calibrate`, `ingest`, `templates`, `validate` | Authenticated API routes, jobs, quotas and persistence |
| `make demo` and the public demo endpoints | Celery workers and object-storage exports |
| `make case`, the example scripts and `make site` | Database migrations and connector features |

`make demo` serves the demo API without writing to the database. If you only
need scenario exploration, you do not need Docker at all.

Verify with `uv run hnle version`, `uv run hnle templates` and
`curl -fsS http://127.0.0.1:8000/health`. `/health` is a liveness check, not a
database check.

## The three surfaces

| Surface | Entry point | Engine | Best for |
|---|---|---|---|
| Hosted demo | <https://cxy2696.github.io/opinionlab/> | Lightweight binary simulator in the browser | A first look, a quick parameter sweep, CSV export |
| Local full service | `make demo` then <http://127.0.0.1:8000/api/v1/demo/app> | The real Python engine through the demo API | Reports, real templates, optional Ollama narration |
| CLI | `uv run hnle ...` | The real Python engine, no server | Reproducible runs, sweeps, calibration, verification |

The hosted page is static: `site/sim.js` runs in the browser with binary
opinions, uniform weights and mean aggregation, uploads nothing, exports CSV and
cannot call Ollama. The fidelity table is in
[Demo](DEMO.md#browser-preview-fidelity). The local service runs the real engine, serves an offline
HTML report and can use local Ollama for narration; its controls expose a subset
of the spec, while the engine supports multi-stance specs, shocks and
interventions.

## Guided first session

Start with the hosted URL, or run `make setup` and `make demo` for the local
surface; only the local page generates the HTML report.

**1. Choose and run.** Pick a template; its question appears. Start with S2:
`q = 1.6`, latency `mu = 3`, 100 steps, seed 42 and 8 replicas. Press **Run
simulation** (or Enter). The status line reports the submitted values.

**2. Read the hero instruments.**

| Instrument | Meaning | How it is computed |
|---|---|---|
| Cohesion gauge | Final agreement | `100 x (1 - mean(diversity_final))` across replicas |
| Peak-turn gauge | Largest single-step switch | `100 x max(cascade)` for the displayed run |
| Replicas | Independent runs behind the estimate | `n` of `diversity_final` |
| Mean majority | Step at which a majority formed | Mean `time_to_consensus` over replicas that reached it; censored replicas are excluded |
| Peak at step | Where the largest burst happened | Argmax of the displayed run's cascade series |
| 95% confidence | Half-width of the final-diversity interval | `(ci95_hi - ci95_lo) / 2` |

The four readouts below the stage are replicas, mean majority step, peak step
and the 95% confidence half-width. The central 3D stage is a decorative
150-node projection, not a data-accurate network plot; do not read node positions
as real relationships.

**3. Read the summary and decision brief.** The verdict is **Stable consensus**
(when most replicas are stable), **Majority reached, still moving** or **Not
converged** (from the displayed replica's consensus time). The metrics card
carries the aggregate estimates: mean, 95% confidence interval and `n` replicas.
The **Decision brief** repeats the decision, timing nodes (takeoff, peak,
consensus, this run's intervention), simulated window, follow-ups and caveat.
Timing values come from the displayed replica, not an aggregate forecast.

**4. Inspect the telemetry and charts.** Terrain height is diversity, column
height is the share switching in a step, and colour is the stance split. Hover
for step values; the deck follows replay. The three charts are diversity (solid
line = this run, dashed = replica median, band = 10th-90th percentile), opinion
shares (stacked) and cascade (share changing stance per step). A wide band means
the result depends on randomness; do not over-read intervals when `n < 30`.

**5. Replay, compare, copy and export.** Replay plays or scrubs the series
without recomputing. Compare becomes available after a second run, toggles a
previous-run overlay on the diversity chart, and reports the change in
`diversity_final` with a CI-overlap check. Copy link stores the
parameters and UI language in the URL; adding `?run=1` runs on load.

- Hosted CSV: `step,diversity,cascade,share0,share1` for the displayed replica,
  not the replica band.
- Local **Report**: one self-contained HTML file with the summary, decision brief,
  narrative and fixed disclaimer.
- CLI run artifacts: `runs/<run_id>/` with the manifest, series CSV
  (`step,diversity,cascade,mean_opinion`), metrics parquet, figure, graph and
  HTML report.

**6. Evidence trail (v1.4.0).** These behaviours are in the current code; the UI
is being upgraded in parallel:

- `/api/v1/demo/simulate` returns a `quality` block with `censored_replicas`,
  `censored_rate`, `insufficient_samples`, `degraded_to_streaming` and warnings,
  and echoes engine, latency and opinion settings in `spec`.
- `/api/v1/demo/templates` returns operator-configured `limits`.
- Aggregate `time_to_consensus` uses a censored Student-t interval over replicas
  that reached consensus; a normal approximation at small `n` is no longer used.
- `init_mode: fixed_ratio` now supports `n_opinions > 2`: stance 1 gets the
  target share and the rest is split as evenly as possible across other stances.
- A decision brief can carry a fourth follow-up when consensus already holds.

## Parameter reference

Ranges below are the Pydantic constraints in
[`spec.py`](../packages/hnle/src/hnle/spec.py). The demo controls are narrower:
`q` 0.5-3, latency 1-60, steps 10-200, replicas 1-20; the demo API caps nodes at
400, steps at 200 and replicas at 20. Latency is measured in **sweeps**, not
seconds; one sweep is one update opportunity for a ready node.

### Dynamics and evidence

| Parameter | Default and valid range | Raising or changing it | Calibrate from real data | Common mistake |
|---|---|---|---|---|
| `q` | 1.5; 0.01-20.0 | Higher makes local majorities pull harder: faster consensus, lower diversity, more concentrated cascades. `q = 1` is the voter limit; `q < 1` flattens toward the stances present in the group. | Fit the diversity curve or consensus time with `hnle calibrate`; start near 1-2 unless you have evidence. | Treating `q` as persuasion strength rather than conformity to the local group; `q = 0` is rejected. |
| `latency.dist` | `normal`; `normal`, `exponential`, `lognormal`, `const` | Changes the shape and tail. `const` removes latency heterogeneity; `exponential` is memoryless; `lognormal` is right-skewed. | Match the observed reaction-time distribution; use `const` only as a baseline. | Setting `mu` under `exponential` while `lambda` is present and expecting `mu` to control the draw. |
| `latency.mu` | 5.0; > 0 | Higher delays updates: the peak moves later, the tail lengthens, and a fixed window censors more often. | Map measured response time to sweeps and fit peak timing. | Treating `mu` as seconds; for `lognormal`, `mu` is a log-scale parameter, not the mean. |
| `latency.sigma` | 2.0; > 0 | Higher spreads reaction speeds, widening the cascade and the tail. Ignored by `const` and `exponential`. | Fit the dispersion of response times; for `lognormal`, this is the log-scale standard deviation. | Changing `sigma` under `const` or `exponential` and expecting a different run. |
| `latency.lambda` | `None`; filled as `1 / mu` for `exponential`; > 0 | Higher rate means shorter mean latency (`1 / lambda`); lower rate delays. | Estimate the event rate per sweep and convert the mean to a rate. | Confusing `lambda` with the mean; under `exponential`, `lambda` wins over `mu`. |
| `n_steps` (demo `steps`) | 1000; 1-200000 | A longer window captures the tail and reduces censoring. It does not change per-step dynamics; cost grows linearly. | Cover the peak plus 30-50 steps and your decision horizon. | Reading `time_to_consensus = -1` as "never converges" when the window was simply too short. |
| `repeats` | 50; >= 1 | More replicas narrow the confidence interval roughly as `1 / sqrt(R)` and stabilise the mean. Cost grows linearly. | Pilot the standard deviation, then choose the count that meets your target half-width; use 30+ for a published estimate. | Over-reading intervals at `n < 30`, or thinking more replicas change the expected result. |
| `seed` | 42; >= 0 | A different seed draws a different sample. The same spec and seed reproduce the run. | Fix it for audit; vary it deliberately to test robustness. | Seed shopping, or comparing runs that differ in both seed and parameters. |

### Population, decisions and consensus

| Parameter | Default and valid range | Raising or changing it | Calibrate from real data | Common mistake |
|---|---|---|---|---|
| `n_opinions` | 2; 2-6 | More stances raise the maximum diversity and entropy, and change every metric that depends on `K`. Binary-only controls are rejected. | Use the coding scheme in your data; keep `K` fixed across comparisons. | Comparing diversity or entropy across different `K` without rescaling; using `flip_share` or `debunk` when `K > 2`. |
| `decision_rule` / `threshold` | `stochastic` / 0.5; rule is `stochastic`, `argmax` or `threshold`; threshold 0.0-1.0 | `argmax` picks the top stance deterministically. `threshold` keeps the status quo unless a strictly more likely stance reaches `tau`; a higher `tau` means fewer switches. | Fit switching propensity from panel or survey data; keep `stochastic` as the probabilistic baseline. | Thinking `threshold` affects the stochastic rule, or confusing it with `consensus_threshold`. |
| `init_mode` / `target_share_1` | `data_driven` / 0.5; mode is `data_driven`, `balanced_random` or `fixed_ratio`; share 0.0-1.0 | `data_driven` uses ingested initial opinions when present, otherwise uniform. `balanced_random` is uniform. `fixed_ratio` fixes the stance-1 share and splits the rest; for `K > 2` the rest is split evenly across the other stances. | Use label shares from ingest or a survey; use `fixed_ratio` for a controlled what-if. | Expecting `target_share_1` to apply under `data_driven` or `balanced_random`, or to set every stance when `K > 2`. |
| `consensus_threshold` | 0.8; 0.5-1.0 | Higher demands a larger largest share: consensus arrives later or not at all. Lower declares consensus earlier. | Set it from the decision's definition of "settled"; do not fit it to force a result. | Calling 0.8 a simple majority; it is an 80% supermajority. Comparing consensus times across different thresholds. |

### Structure, weights and events

| Parameter | Default and valid range | Raising or changing it | Calibrate from real data | Common mistake |
|---|---|---|---|---|
| `aggregation` | `mean`; `mean`, `size_weighted`, `max` | `mean` averages incident edges. `size_weighted` gives larger groups more weight. `max` renormalises the elementwise maximum: "the strongest group wins", not an average. | Compare plausible group-influence assumptions; `mean` is the reference. | Reading `max` as a convex combination or an average of group opinions. |
| `weights.source` / `weights.normalize` | `uniform` / `max`; source is `uniform`, `engagement`, `centrality` or `custom`; normalize is `max` or `none` | `engagement` uses ingested node weights; `centrality` uses incidence degree; `custom` maps node ids. `max` rescales to peak 1; `none` leaves the scale, which cancels globally. | Use observed interaction volume or degree; use `custom` for expert weights. | Using `engagement` on a synthetic graph (it falls back to ones with a warning), entering negative weights (rejected), or expecting normalization to change relative influence. |
| `hyperedge.min_size` / `max_size` | 2 / 200; both >= 2 and `max_size >= min_size` | Larger groups mix more, usually speeding consensus and enlarging cascades. Smaller groups preserve local clusters. | Match observed thread, meeting or group sizes. | Requesting more distinct edges than the graph can contain, or setting `min_size` above `n_nodes`; both fail. |
| `topology.mode` / `arrival_rate` / `decay_rate` | `static` / 0.0 / 0.0; rates >= 0 | `time_varying` adds `Poisson(arrival_rate)` edges per step and drops `round(decay_rate x edge count)` edges. Higher arrival grows mixing; higher decay fragments. | Estimate edge births and deaths per sweep from timestamped data. | Turning it on with too short a window, or treating synthetic new edges as real recommender behaviour. |
| `shocks` | `[]`; `at_step >= 0`, `type` is `flip_share`, `edge_boost` or `new_opinion`, `magnitude` 0.0-1.0, `duration >= 1` | One-shot events at `at_step`. `flip_share` flips a share; `new_opinion` assigns random stances; `edge_boost` adds a probability bias at that step. Higher magnitude changes more nodes or adds more bias. | Set timing and reach from event logs; change one event at a time. | Treating a shock as a sustained campaign; `flip_share` and `edge_boost` are binary-only. |
| `interventions` | `[]`; `at_step >= 0`, `type` is `boost`, `dampen`, `debunk`, `seed_opinion` or `weight_shift`, `magnitude` 0.0-1.0, `duration` 1-1000 | `boost`, `dampen` and `weight_shift` bias the probability over the duration window. `debunk` and `seed_opinion` act only at `at_step`; their `duration` does not spread them. | Set timing, reach and duration from campaign records; use one change per run. | Expecting `duration` to spread a debunk; using `boost`, `dampen`, `debunk` or `weight_shift` when `K > 2`; treating `debunk` as stance-neutral. |

`ModelSpec.metrics` selects which aggregate metric keys are returned by
`run_monte_carlo` and therefore by the CLI and the API. The engine computes the
full metric set internally; a requested subset only filters the output. The CLI
prints a note instead of failing when `diversity_final` is excluded, and
`hnle sweep` raises with the available keys if its `--metric` is not selected.

Two validation rules matter in practice:

- `engine: event_driven` requires `latency.quantize: integer_steps`. Use
  `sparse_vector` for continuous latency.
- `graph.n_nodes` and `graph.n_edges` live in the scenario YAML, not in
  `ModelSpec`. The generator rejects impossible edge counts and edges smaller
  than `min_size`.

## Metric dictionary

Every aggregate metric has the same shape: `mean`, `ci95_lo`, `ci95_hi` and `n`.
The formulas below use the final share `p_v` of stance `v` and `K` stances.

| Metric | Plain meaning and formula | How to read it | Caveat |
|---|---|---|---|
| `diversity_final` | `1 - max_v p_v`. 0 means unanimity; `1 - 1/K` means an even split. | Lower means one stance dominates. | It measures concentration, not the number of opinions or the intensity of disagreement. |
| `entropy_final` | `-sum_v p_v log2(p_v)` in bits. 0 is unanimity; `log2(K)` is an even split. | Higher means more evenly spread opinions. | Depends on `K`; compare only runs with the same number of stances. |
| `polarization_final` | `(1 - sum_v p_v^2) / (1 - 1/K)`. 0 is unanimity; 1 is an even split. | Higher means a more dispersed distribution. | It is a dispersion index, not a measure of two hostile camps. With `K > 2` it does not mean "bipolar". |
| `n_active_opinions` | Count of stances with `p_v > 0`. | How many stances survive at the end. | A single surviving node counts. There is no minimum-share filter. |
| `assortativity` | `(observed - expected) / (1 - expected)` over all member pairs of all hyperedges; `expected = sum_v p_v^2`. +1 means every hyperedge is homogeneous; 0 is chance. | Positive means like-minded groups; negative means mixing. | Pair counts are not independent, and hyperedge overlap is not modelled as causation. |
| `time_to_consensus` | First step `t` where `1 - diversity_t >= consensus_threshold`; otherwise `-1`. | Smaller is earlier. `0` means the initial state already qualified. | Censoring: `-1` means no majority formed inside the window, not "never". Never average `-1` as zero. |
| `consensus_stability` | 1.0 when consensus holds for `ceil(max_latency)` further steps after first being reached; 0.0 otherwise. The aggregate mean is the share of replicas that were stable. | Near 1 means consensus persisted. | Requires enough remaining series; a short window can return 0 even if consensus formed near the end. |
| `absorbing` | In `summarize`, this is the same flag as `consensus_stability`; the aggregate mean is the fraction of stable replicas. | A population-level label for "consensus reached and held". | It is not a formal graph absorbing state. On a fragmented graph, components can freeze while the population flag stays false; inspect components. |
| `runaway` | Legacy boolean: `time_to_consensus < 0`. | Alias for censoring. | It is not evidence of explosive growth. The aggregate mean is the censored fraction. |
| `cascade_p50`, `cascade_p90`, `cascade_p99`, `cascade_max` | Percentiles and maximum of the per-step cascade series, where each step is the share of nodes changing stance. The aggregate value is the mean of the per-replica quantiles. | Higher p99 or max means a larger burst; p50 describes a typical step. | A finite window and a single peak make p99 unstable. Do not compare p99 across different step counts without care. |
| `oscillation_zero_crossing_rate` / `oscillation_autocorr` | Sign changes per step of the detrended mean-opinion series / lag-1 Pearson autocorrelation. | More crossings and negative autocorrelation mean alternation; positive autocorrelation means persistence. | Detrending choices change the value, and a near-zero autocorrelation can hide a cycle longer than the window. |
| `oscillation_power_ratio` / `oscillation_dominant_freq` / `oscillation_sign_persistence` | Dominant non-DC FFT power share, dominant frequency in cycles per step, and agreement of consecutive first-difference signs. `oscillating` is true when the power ratio is at least 0.5. | A stronger cycle, a shorter period and smoother movement. | Short series are unreliable; the 0.5 cut-off is a heuristic, not a hypothesis test. |

### Censoring, intervals and multiple comparisons

- `time_to_consensus = -1` is **censored**, not zero and not infinity: no step in
  `n_steps` reached the largest-share threshold. The aggregate `time_to_consensus`
  uses only replicas that reached consensus; `n` is that count, `mean` is `null`
  when none did, and `quality.censored_rate` carries the censoring rate.
- The engine uses a Student-t interval, `mean +/- t(0.975, R-1) * sqrt(var / R)`.
  For `R >= 30`, `t` is close to 1.96; for small `R` it is wider, and `R = 1`
  gives a zero-width interval that is not evidence. `R < 30` emits an
  underpowered warning and sets `quality.insufficient_samples`.
- Reporting many metrics gives no simultaneous coverage. A single 95% interval
  that excludes zero is not a family-wise result. Pre-specify the primary metric
  and avoid cherry-picking the one significant comparison.
- `hnle compare` uses percentile bootstrap intervals, not the Student-t
  interval. Non-overlapping intervals are a screening rule, not proof of a real
  effect.

## Scenario library

The repository has 16 templates: 15 enabled and G5 gated. Each row names the
decision, typical user and signal; the full question, assumptions and limitations
are in the template YAML.

| Key | Template | Decision it informs | Typical user | Signal to watch |
|---|---|---|---|---|
| G1 | Academic reproduction | Whether behaviour matches the classical voter limit | Researcher, lecturer | Consensus probability falling with `n`; `q = 1`, `L = 1`, pair edges |
| G2 | Fact checking | When fact-checking should step in | Trust and safety, fact-check desk | Earlier checks shorten the cascade tail; overlapping CIs mean timing is not the driver |
| G3 | Public health | When to concentrate authoritative messaging | Public-health communications | A higher seeded share converges faster, but over-concentration can suppress diversity |
| G4 | Platform systemic risk | Observation windows for platform risk | Platform risk, regulatory | Topology growth plus high `q` raises cascade p99 and delays convergence |
| G5 | Election academic (GATED) | Compliance boundary for election research | Approved academic researcher | Cyclical structure only; never election forecasting |
| G6 | Disaster warning | When to issue a warning | Emergency management | Positive share rises quickly and does not revert |
| G7 | Corporate change communication | Cadence of change communication | Internal communications, HR | Staged communication softens the shock; long gaps let negative opinions regroup |
| S1 | Policy release cadence | Cadence and window for staged policy | Policy team | A fast diversity drop after the peak means one narrative; high post-intervention cascades need a longer window |
| S2 | Rumor debunk timing | Timing and strength of debunking | Communications, trust and safety | Earlier debunking lowers the negative share; overlapping CIs do not establish a timing effect |
| S3 | Platform governance | When to intervene with moderation | Platform governance | Lower cascade p99 and faster convergence; otherwise discussion may move elsewhere |
| S4 | Brand KOL mix | Mix and cadence of KOL versus organic reach | Brand, marketing | Higher KOL weight gives a larger early cascade but lower late diversity |
| S5 | Emergency science literacy | When to push emergency science communication | Public-health, emergency communications | Earlier communication raises the positive share; long latency needs repeated authoritative reach |
| S6 | Financial expectation communication | Cadence of regulator communication | Regulator, central-bank communications | Gradual communication lowers p99 but can lengthen convergence |
| S7 | Community consensus | Whether and when to facilitate a discussion | Community facilitator, local government | A shorter consensus step without diversity collapsing to zero |
| S8 | Organizational change | Cadence and window for change communication | Internal communications, HR | Lower cascade p99 with moderate diversity after damping |
| S9 | Product launch | Launch cadence for a new product | Product marketing | Early cascade size is not durable word of mouth; watch late diversity and negative share |

G5 is disabled by default behind `ff_g5_election_templates`. Enabling it requires
use-case review: an `org_admin` declaration and a `platform_admin` approval. An
unapproved clone returns `403 USE_CASE_NOT_APPROVED`, and election forecasting is
prohibited regardless of approval.

## Worked interpretations

**1. Overlapping intervals.** If early-debunk and late-debunk runs have
overlapping final-negative-share CIs, conclude that this run does not establish a
timing difference. Do not conclude that timing never matters; add replicas,
calibrate latency, or narrow the comparison.

**2. Censored consensus.** If `time_to_consensus = -1` and
`quality.censored_replicas > 0`, conclude that no majority formed inside the
window. Do not report zero and do not conclude that the group will never
converge; extend `n_steps` or inspect fragmentation.

**3. High cascade p99 with low final diversity.** If `cascade_p99` is high while
`diversity_final` is low, conclude that a large burst compressed the group into a
dominant stance. Do not call it healthy debate or a forecast of a real spike;
check whether the peak is early or late and whether the band is wide.

**4. Consensus with a surviving minority.** If consensus is reached and
`absorbing` is near 1 but `diversity_final` is around 0.2, conclude that an 80%
supermajority formed while a minority persisted. Do not call it unanimity; the
threshold is 0.8, not 1.0.

## CLI cookbook

Run these from the repository root after `make setup`.

```bash
uv run hnle templates
uv run hnle validate --spec scenarios/s2_rumor_debunk_timing.yaml
```

**Simulate and export.** `simulate` is also the export path; there is no
separate `hnle export` subcommand.

```bash
uv run hnle simulate --spec scenarios/s2_rumor_debunk_timing.yaml \
  --repeats 20 --set q=1.8 --set latency.mu=3 --jobs 4 --out-dir runs
```

The command prints the run id and artifact directory, which contains
`manifest.json`, `<run_id>.series.csv`, `<run_id>.metrics.parquet`,
`<run_id>.figure.png`, `<run_id>.report.html` and `graph.npz`.

**Verify a run from its manifest.** This rebuilds the run and compares
`diversity`, `cascade` and `mean_opinion` with zero tolerance; it does not
recompute the Monte Carlo intervals.

```bash
uv run hnle report --run-id <run_id> --runs-dir runs
```

**Sweep and rank influence.** Add `--lhs 64` for Latin-hypercube samples and
`--sobol` for a first-order variance-effect score.

```bash
uv run hnle sweep --spec scenarios/s2_rumor_debunk_timing.yaml \
  --grid "q=0.8:2.4:5" --grid "latency.mu=2,4,6" \
  --repeats 3 --out sweep.csv --sensitivity-out sensitivity.json
```

**Compare a baseline with single-override variants.** The same seed set is used;
a variant is labelled only when its bootstrap interval does not overlap.

```bash
uv run hnle compare --spec scenarios/s3_platform_governance.yaml \
  --variant q=2.0 --variant latency.mu=5 --repeats 30 --out compare.json
```

**Calibrate against a target diversity series.** The target CSV needs a
`diversity` column; the command runs one replica per grid point and writes the
best RMSE.

```bash
uv run hnle calibrate --spec scenarios/s2_rumor_debunk_timing.yaml \
  --target runs/<run_id>/<run_id>.series.csv \
  --grid q=1.2,1.6,2.0 --grid latency.mu=2,3,4 --out calibration.json
```

**Ingest a CSV and run the graph.** The CLI writes `<csv-stem>.npz` and a
`.stats.json`. `--org-salt` is required; the error mentions `PSEUDONYM_HMAC_KEY`,
but the CLI reads only the option.

```bash
uv run hnle ingest --csv data/kaggle_sentiment.csv --org-salt "$PSEUDONYM_SALT" \
  --mapping scenarios/mappings/kaggle_valence.yaml \
  --user-column User --hashtags-column Hashtags \
  --sentiment-column Sentiment --engagement-column engagement \
  --allow-content --out-dir datasets

uv run hnle simulate --spec examples/kaggle_case.yaml \
  --graph datasets/kaggle_sentiment.npz --repeats 30
```

## API cookbook

Start with `make demo`. The demo API is under `/api/v1/demo`; the interactive
OpenAPI page is <http://127.0.0.1:8000/docs>.

**List templates (`GET`).**

```bash
curl -s http://127.0.0.1:8000/api/v1/demo/templates | python -m json.tool
```

The response contains `data` (templates and `defaults`), `features.ollama`,
`limits` and `disclaimer_key`.

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/demo/simulate \
  -H 'Content-Type: application/json' \
  -d '{"template_key":"S2","q":1.8,"latency_mu":3,"repeats":8,"seed":42,"steps":120}'
```

**Response shape (`POST /api/v1/demo/simulate`).** Values vary:

```json
{"data": {
  "spec": {"q": 1.8, "n_steps": 120, "repeats": 8, "seed": 42, "engine": "sparse_vector",
           "latency_mu": 3.0, "latency_sigma": 1.0, "latency_dist": "normal",
           "n_opinions": 2, "consensus_threshold": 0.8},
  "metrics": {"diversity_final": {"mean": 0.31, "ci95_lo": 0.27, "ci95_hi": 0.35, "n": 8},
              "time_to_consensus": {"mean": 43.2, "ci95_lo": 37.1, "ci95_hi": 49.3, "n": 6}},
  "quality": {"replicas": 8, "censored_replicas": 2, "censored_rate": 0.25},
  "series": {"steps": [0, 1], "diversity": [0.50, 0.49], "cascade": [0.0, 0.04],
             "shares": [[0.5, 0.5], [0.51, 0.49]],
             "bands": {"p10": [], "p50": [], "p90": []}},
  "summary_text": {"verdict_en": "Not converged", "text_en": "Under these assumptions ..."},
  "decision": {"decision_en": "timing and strength of debunking or corrections",
               "timing": {"takeoff_step": 4, "peak_step": 12, "consensus_step": null,
                          "intervention_step": 20},
               "window_en": "A simulated window is steps 6-12 ...", "caveat_en": "..."},
  "disclaimer": "This result is a scenario simulation under stated assumptions, not a prediction of real public opinion."
}}
```

| Block | Meaning |
|---|---|
| `metrics` | Aggregate means and 95% Student-t intervals, keyed by metric. `time_to_consensus` is censored: `n` counts only replicas that reached consensus and `mean` is `null` if none did. |
| `quality` | Evidence flags: graph size, replica count, censored replicas and rate, `insufficient_samples`, streaming degradation and warnings. |
| `series` | Group-level series. `steps` starts at 0; `cascade` has a leading 0; `bands` are the 10th, 50th and 90th percentiles across replicas. |
| `summary` | The displayed replica's full metric set, not the aggregate (not shown in the excerpt). Use `metrics` for group estimates. |
| `decision` | Decision brief for the displayed replica: decision, timing nodes, simulated window, follow-ups and caveat. |
| `summary_text` | English and Chinese verdict and narrative strings; the English fields are `verdict_en` and `text_en`. |
| `disclaimer` | The fixed product disclaimer; keep it with every shared result. |

**Report and narrate (`POST`), plus service checks (`GET`).**

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/demo/report \
  -H 'Content-Type: application/json' \
  -d '{"template_key":"S2","q":1.6,"repeats":8}' -o report.html

curl -s -X POST http://127.0.0.1:8000/api/v1/demo/narrate \
  -H 'Content-Type: application/json' \
  -d '{"template_key":"S2","lang":"en"}'

curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/metrics | head
```

`/narrate` returns `503 OLLAMA_DISABLED` unless `OLLAMA_ENABLED=true`. `/health`
is a liveness probe, `/metrics` is the Prometheus surface and `/docs` is OpenAPI.
Request fields: `template_key` (default `S2`), optional `q`, optional
`latency_mu`, `repeats` (default 8, max 20), `seed` (default 42), optional `steps`
(max 200) and `lang` for narration (`zh`, `en`, `ja` or `de`).

## Deployment

### Full Docker Compose

```bash
cp .env.example .env   # then edit secrets
docker compose up -d --build
curl -fsS http://127.0.0.1:8000/health
```

Compose runs PostgreSQL 16, Redis 7.2, MinIO, the API and a worker. The API
publishes port 8000; PostgreSQL is bound to `127.0.0.1:5432`; the worker has an
8 CPU / 16 GB limit. Apply migrations with `uv run alembic upgrade head` or the
equivalent command inside the API image.

### Kubernetes and air-gapped delivery

The values files are [`deploy/k8s/helm-cn/values.yaml`](../deploy/k8s/helm-cn/values.yaml)
and [`deploy/k8s/helm-global/values.yaml`](../deploy/k8s/helm-global/values.yaml).
They define region, domain, image tag, bucket, storage class, secret names,
ingress TLS secret and worker queues. Use the chart templates supplied with your
deployment environment and pin the image digest.

The [air-gapped guide](../deploy/private/OFFLINE.md) covers image loading, the
bill of materials, secrets, `alembic upgrade head`, chart installation and
verification. Verify image digests, `/health`, `/metrics`, a smoke run with the
disclaimer and a cross-region `403 REGION_MISMATCH` before go-live. A demo-only
host can run `docker compose -f docker-compose.demo.yml up --build`.

### Production checklist

| Area | Check |
|---|---|
| Secrets | No default `JWT_SECRET`, database password, MinIO key or HMAC salt; `.env` is not committed |
| Limits and caps | Set the four rate buckets, `DEMO_MAX_NODES`, `DEMO_MAX_STEPS`, `DEMO_MAX_REPEATS` and worker quotas |
| TLS | Provide the ingress TLS secret; terminate TLS before the API |
| Backups | Back up PostgreSQL, MinIO objects and Redis AOF; restore-test them |
| Migrations | Run `alembic upgrade head` before serving; revert only reversible migrations |
| Observability | Scrape `/metrics`, ship structured logs, keep `trace_id`, and wire the Runbook alerts |
| Region and review | Set `REGION`; keep `USE_CASE_REVIEW_ENABLED=true` and the G5 approval gate |
| Rollout and reports | Canary one API and one worker; keep the previous digest; every report needs the fixed disclaimer |

## Data and privacy

- The contract is **aggregate-only**: no endpoint or report may return a per-node
  trajectory (`NODE_TRACE_FORBIDDEN`). User IDs are HMAC-SHA256 pseudonymised
  before the engine, and raw phone, ID, email and nickname columns are rejected.
- The hosted demo uploads nothing; the local demo needs no login and its public
  endpoints do not write to the database.
- Datasets, graph snapshots, runs, artifacts and sharing mappings are deleted
  together; the scenario remains but is detached. The documented retention
  default is 180 days, audit logs are append-only for at least 180 days, and file
  logs rotate daily with a 7-day window.
- CN and EU deployments are isolated; cross-region tenant access returns
  `403 REGION_MISMATCH`. Prohibited uses include individual prediction, profiling
  or scoring; election forecasting; targeted persuasion; covert monitoring or
  re-identification; and any use that violates local law.
- Optional Ollama narration is off by default, uses a local endpoint, changes no
  metric or decision, and must stay labelled as an AI-assisted explanation.

## Troubleshooting and FAQ

| Symptom | Check | Fix |
|---|---|---|
| Port 8000 is in use | `lsof -i :8000` | Stop the other process, or run `uv run uvicorn app.main:app --port 8001` |
| Docker is unavailable | `docker --version` | `make setup` already skips it; install Docker or point `.env` at external PostgreSQL, Redis and MinIO |
| Database errors on service routes | `DATABASE_URL`; container health | Start `db` and run `uv run alembic upgrade head`; `/health` alone does not test the database |
| Ollama button is disabled | `OLLAMA_ENABLED` | Set it to `true`, run `ollama serve`, `ollama pull llama3.2`; the hosted page cannot use Ollama |
| Confidence intervals are wide | `n` and `quality.insufficient_samples` | Raise `repeats` to 30+ and report the range; do not narrow it by cherry-picking |
| No majority result | `time_to_consensus` and `censored_rate` | `-1` is censoring, not zero; extend `n_steps`, check the threshold and inspect fragmentation |
| A large sweep is slow or memory-heavy | Number of grid points and replicas | Use `--lhs`, fewer points, fewer replicas, and batch axes; `--jobs` raises CPU but also peak process memory |
| Browser demo lacks a feature | The surface | The hosted demo is binary, uniform-weight and capped; use the local service or CLI for multi-stance specs, reports and shocks |

## Glossary

| Term | Meaning |
|---|---|
| Node / hyperedge | A node is an opinion holder; a hyperedge is a group interaction containing two or more nodes |
| Replica | One independent run of the same spec with its own seed stream |
| Conformity `q` | Exponent that amplifies the local majority; `q = 1` is the voter limit |
| Latency | Minimum sweeps between a node's updates; drawn per node |
| Sweep / step | One synchronous update opportunity in the observation window |
| Cascade | Share of nodes changing stance in a single step |
| Censoring | No threshold crossing inside the window; recorded as `time_to_consensus = -1` |
| Confidence interval | 95% Student-t interval for the mean over replicas; `compare` uses a bootstrap interval |
| Absorbing / runaway | Consensus held for one max-latency window / legacy alias for a censored consensus time, not explosive growth |
| Diversity, entropy, polarization, assortativity | Concentration, spread, normalised dispersion and like-minded-group tendency of the final distribution |
| Shock / intervention | One-shot external event / timed boost, dampen, debunk, seed or weight shift |
| Pseudonymisation | Keyed HMAC replacement of user identifiers before ingest |
| G5 / use-case review | The gated election-research template and its approval workflow |

## Related documents

| Document | Contents |
|---|---|
| [Docs index](README.md) | Reading paths and the full document list |
| [Demo](DEMO.md) | Hosted and local interfaces, API, limits and Ollama |
| [Use cases](USE_CASES.md) | Six worked questions with commands and interpretation |
| [Math model](MATH_MODEL.md) | Normative equations, estimators and failure boundaries |
| [Model card](MODEL_CARD.md) | Capabilities, limitations and prohibited uses |
| [Compliance](COMPLIANCE.md) | Regions, review, retention, deletion and red lines |
| [Runbook](RUNBOOK.md) | Metrics, logs, alerts, rollback and tainted runs |
| [Case study](CASE_STUDY.md) | A real fragmented hashtag graph end to end |
| [Air-gapped delivery](../deploy/private/OFFLINE.md) | Offline installation, verification and rollback |
| [Changelog](../CHANGELOG.md) | Behaviour changes and release history |
