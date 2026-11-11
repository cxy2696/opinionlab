# Math model

This document is the normative definition of the OpinionLab model. Code and
tests follow it; the README only summarises it. Each formula is mapped to a
function so that a change in one engine cannot silently diverge from another.

## 1. State and assumptions

- Hypergraph `H = (V, E)`: `V` are nodes (people, accounts, teams); `e ∈ E` is a group interaction (topic, chat, meeting), `|e| ≥ 2`.
- Node weights `α_j ≥ 0`: non-negative influence weights. Sources are `uniform` (all ones), `engagement` (per-node engagement stored on the ingested graph), `centrality` (incidence degree), and `custom` (explicit mapping). `max` normalisation rescales to a maximum of one; a global rescaling cancels in the conformity map.
- Opinions `X_i ∈ {0, …, K−1}`; the default is `K = 2`.
- Latency `L_i ≥ 0`: minimum interval between updates; `T_i` is the last sweep at which node `i` changed opinion.
- Decision rule `decision_rule ∈ {stochastic, argmax, threshold}`.

Zero weights are allowed for custom sources: they make a node silent in the
weighted counts. An edge whose total weight is zero has no information, so the
engine falls back to the uniform distribution and counts a
`zero_denominator_edges` warning. Negative weights are rejected: they would
make `S_x` negative and the power map undefined for fractional `q`.

## 2. Weighted edge distribution

For hyperedge `e` and stance `x`:

```
S_x(e) = Σ_{j∈e} α_j · 1(X_j = x)
```

`S_x` is a weighted count, not a normalised share. The scale of the weights
cancels in the next step, so only their relative sizes matter.

## 3. Nonlinear conformity map

```
p_x(e) = S_x(e)^q / Σ_u S_u(e)^q          (q > 0)
```

For `q > 0`, a stance that is absent from the edge has `S_x = 0` and therefore
zero probability. If the edge total is zero, the engine uses `p_x = 1/K`.
`q = 0` is rejected: the limit `q → 0+` is uniform over the *present* stances,
but the exact expression at `q = 0` depends on the convention for `0^0` and
would give mass to absent stances under NumPy's convention.

| Case | Behaviour |
|---|---|
| `q → 0+` | uniform over the stances present in the edge; the size of the majority is ignored |
| `q = 1` | linear voter: probability proportional to the weighted share |
| `q → ∞` | mass concentrates on `argmax_x S_x(e)`; ties split equally |

Code: `hnle/core/kernel.py::conformity_probabilities`.

## 4. Node aggregation and update

Let `E_i` be the incident hyperedges of node `i`. Aggregate their probability
vectors into `p_i = A_{e∈E_i} p(e)`. The aggregation `A` is one of:

- **`mean`** (default): the arithmetic mean of the incident distributions. It is
  a convex combination, reduces to `p(e)` when `|E_i| = 1`, and is order
  independent.
- **`size_weighted`**: a convex combination with weights proportional to
  `|e|`; larger groups count more.
- **`max`**: the element-wise maximum of the incident distributions,
  **renormalised** to sum to one. This is a heuristic for "the strongest group
  wins". It is not a convex combination and has no interpretation as an average
  of group opinions; the renormalisation is what makes it a probability
  distribution.

Then:

- **Readiness:** `t − T_i ≥ L_i`. A node that does not change stays eligible on
  the next sweep; a node that changes is blocked for `L_i` sweeps.
- **Stochastic** (default): `X_i(t+1) ~ Categorical(p_i)`.
- **argmax:** `X_i(t+1) = argmax_v p_i(v)`; ties go to the lowest stance index.
- **threshold:** switch to the most likely stance only when it is **strictly
  more likely than the current stance** and its probability is at least `τ`;
  otherwise keep the current stance. Ties keep the status quo. This is why the
  rule needs the current opinion as well as `p_i`.

Discrete kernels write atomically at the end of a sweep. The event kernel uses
the same clock rule; with integer latencies the two agree step by step
(`tests/test_engine_equivalence.py`).

## 5. Engines

- **CSR sparse (default):** synchronous sweeps. All ready nodes are updated
  from the state at the start of the sweep. This is the reference semantics.
- **Event driven:** integer latency only. A node that changes is due again
  after `L_i`; a node that does not change is due on the next sweep. Series are
  recorded on every integer sweep, so they are comparable with the CSR series.
  Continuous latency is handled by the CSR engine; the event engine rejects it
  at validation time.
- **Binary special case.** For `K = 2`, positive weights and finite latencies, a
  state is absorbing if and only if every connected component of the hypergraph
  is unanimous. On a disconnected graph the process freezes into a mosaic of
  component opinions, so the population-level `absorbing` flag can be false even
  when every component has frozen. Read `absorbing` and `runaway` as
  population-level labels, and inspect the component structure when the graph is
  fragmented. The proof and the consequences are in the accompanying HNL
  revision (`docs/MODEL.md` in the `Hypergraph-Nonlinear-Latency-Voter-Model`
  repository).

## 6. Monte Carlo estimator and intervals

Run `R` independent replicas of the same `ModelSpec`, yielding metrics
`Y_1, …, Y_R`:

```
mean = (1/R) Σ_r Y_r
var  = (1/(R−1)) Σ_r (Y_r − mean)^2
CI95 = mean ± t_{0.975, R−1} · sqrt(var / R)
```

Implementation: `hnle/mc.py` (Welford updates to avoid drift at larger `R`).

**Rigour notes:**

- The interval is a Student-*t* interval, not a normal approximation. For
  `R ≥ 30`, `t ≈ 1.96`; for small `R` it is wider. `R < 30` emits an
  underpowered warning.
- Reporting several metrics gives no simultaneous coverage guarantee; do not
  cherry-pick one significant result.
- Replicas must be independent; shared streams understate variance, so each
  replica gets a `SeedSequence` split.
- Consensus-time metrics are **censored** when no majority forms inside the
  window. `time_to_consensus = −1` records this; report the censoring rate and
  do not treat "not reached" as zero. The legacy `runaway` boolean is an alias
  for this condition, not evidence of explosive growth.

## 7. Reproducibility and invariants

- Hyperedges are sorted, duplicate node ids are rejected, and duplicate edges
  are merged before aggregation; float summation order is fixed and a node
  permutation leaves results unchanged.
- Each replica uses independent `SeedSequence.spawn(3)` streams for initial
  opinions, latencies and decisions.
- Metrics use float64; tests use `numpy.testing.assert_allclose`, never `==`.
- The API and reports expose group-level statistics only; per-node traces are
  rejected at the boundary.

## 8. Formula-to-code map

| Formula | Code |
|---|---|
| `S_x(e) = Σ α_j 1(X_j=x)` | `core/update.py::edge_distributions`, `core/sparse.py::_node_probabilities` |
| `p_v(e) = S_v^q / Σ S_u^q` | `core/kernel.py::conformity_probabilities` |
| readiness `t − T_i ≥ L_i` | `core/update.py::run_simulation`, `core/event.py::run_event` |
| aggregation `mean / max / size_weighted` | `core/update.py::aggregate_node_probabilities`, `core/kernel.py::normalize_rows` |
| `diversity = 1 − max_v share_v` | `metrics.diversity` |
| `entropy = −Σ p log p` (bits in code) | `metrics.shannon_entropy` |
| oscillation: FFT peak ratio, zero crossings, lag-k autocorrelation | `metrics.fft_power_ratio`, etc. |
| consensus / censoring | `core/kernel.py::reached_consensus`, `metrics.time_to_consensus` |
| replica cost `c·nnz·steps` | `hnle/capacity.py` (measured `c ≈ 1.5e-8`) |

## 9. Assumptions and failure boundaries

- Topology and weights come from the supplied data; the model does not infer
  real relationships or model recommender systems, media agenda or offline
  behaviour.
- `q`, latency and initial stances must be calibrated externally; without
  calibration, conclusions are directional only.
- This is scenario simulation, not causal identification: a change after
  varying a parameter is not a causal effect of a real intervention.
- Individual prediction, profiling or scoring is outside the model's promises
  and violates product red lines.
