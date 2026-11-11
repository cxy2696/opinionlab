# Math model

> **In one minute**
>
> - `q` controls majority-following: `q=1` is the linear voter, `q→∞` locks onto the majority.
> - The 95% CI is a normal approximation over replicas; treat `R<30` as directional only.
> - This is scenario simulation, not causal identification; do not over-claim without calibration.

This document states the update rule as checkable mathematics and maps every formula to code. The
goal is not to look like a paper, but to make each number answer three questions: **what it defines,
which assumptions it depends on, and when it should not be trusted.**

## 1. Notation and state

- Hypergraph `H = (V, E)`: `V` are nodes (people, accounts, teams); `e ∈ E` is a group interaction
  (topic, chat, meeting).
- Node weights `α_j > 0`: normalised by engagement by default; uniform weights give `α_j = 1`.
- Opinions `X_i ∈ {1, …, K}`; V1 defaults to `K=2` but the engine supports multiple stances.
- Latency `L_i ≥ 0`: minimum interval between updates; `T_i` is the last change time.
- Decision rule `decision_rule ∈ {stochastic, argmax, threshold}`.

## 2. Weighted edge distribution

For hyperedge `e` and stance `x`:

```
S_x(e) = Σ_{j∈e} α_j · 1(X_j = x)
```

`S_x` is a **weighted count**, not a normalised share; the scale cancels below. Node aggregation
defaults to `mean` over incident edges, with `max` and `size_weighted` also supported.

## 3. Non-linear conformity map

Binary case:

```
p_1(e) = S_1(e)^q / (S_0(e)^q + S_1(e)^q)
p_0(e) = 1 - p_1(e)
```

Multi-stance case:

```
p_v(e) = S_v(e)^q / Σ_u S_u(e)^q
```

Limits of `q` (this is what the interpretation rests on):

| Case | Behaviour |
|---|---|
| `q → 0` | probabilities tend to uniform `1/K` over non-empty stances |
| `q = 1` | linear voter: probability proportional to the weighted share |
| `q → ∞` | mass concentrates on `argmax_x S_x(e)`; ties split equally |

Code: `core/update.py::edge_distributions`, `core/sparse.py::_node_probabilities`.

## 4. Node aggregation and update

Let `E_i` be the incident hyperedges of node `i`. Aggregate their probability vectors:

```
p_i = A_{e∈E_i} p(e)
```

`A` is `mean`, `max` or `size_weighted`. Then:

- **Readiness:** `t - T_i ≥ L_i`; nodes that are not ready do not update this step.
- **Stochastic rule** (default): `X_i(t+1) ~ Categorical(p_i)`, matching the upstream dynamics.
- **argmax rule** (the deterministic form of paper equation (3)): `X_i(t+1) = argmax_v p_i(v)`.
- **threshold rule:** switch only when `max_v p_i(v) ≥ τ`; otherwise keep the current stance.

The discrete kernel writes atomically at the end of a step; the event kernel reschedules by `L_i`.
With `L_i ≡ 1` both kernels agree step by step (`tests/test_engine_equivalence.py`).

## 5. Monte Carlo estimator and intervals

Run `R` independent replicas of the same `ModelSpec`, yielding metrics `Y_1, …, Y_R`:

```
mean = (1/R) Σ_r Y_r
var  = (1/(R-1)) Σ_r (Y_r - mean)^2
CI95 ≈ mean ± 1.96 · sqrt(var / R)
```

Implementation: `hnle/mc.py` (Welford updates to avoid drift at larger `R`).

**Rigour notes:**

- The interval is a **normal approximation**; for small `R` treat it as directional only. `R < 30`
  emits an underpowered warning.
- Reporting several metrics gives no simultaneous coverage guarantee; do not cherry-pick one
  significant result.
- Replicas must be independent; shared streams understate variance, so each replica gets a
  `SeedSequence` split.
- Consensus-time metrics are **censored** when no majority forms inside the window; report the
  censoring rate instead of treating “not reached” as zero.

## 6. Reproducibility and invariants

- Hyperedges are sorted before aggregation; float summation order is fixed and node permutation
  leaves results unchanged (verifiable at `atol=0`).
- Each replica uses independent `SeedSequence.spawn(3)` streams for init, latency and decisions.
- Metrics use float64; tests use `numpy.testing.assert_allclose`, never `==`.
- The API and reports expose group-level statistics only; per-node traces are rejected at the boundary.

## 7. Formula-to-code map

| Formula | Code |
|---|---|
| `S_x(e) = Σ α_j 1(X_j=x)` | `core/update.py::edge_distributions`, `core/sparse.py::_node_probabilities` |
| `p_v(e) = S_v^q / Σ S_u^q` | same |
| readiness `t - T_i ≥ L_i` | `core/update.py::run_simulation` |
| aggregation `mean/max/size_weighted` | `aggregate_node_probabilities` |
| `diversity = 1 - max_v share_v` | `metrics.diversity` |
| `entropy = -Σ p ln p` (bits in code) | `metrics.shannon_entropy` |
| oscillation: FFT peak ratio, zero crossings, lag-k autocorrelation | `metrics.fft_power_ratio`, etc. |
| convergence / absorbing state | `metrics.time_to_consensus`, `consensus_stability` |
| replica cost `c·nnz·steps` | `hnle/capacity.py` (measured `c≈1.5e-8`) |

## 8. Assumptions and failure boundaries

- Topology and weights come from the supplied data; the model does not infer real relationships or
  model recommender systems, media agenda or offline behaviour.
- `q`, latency and initial stances must be calibrated externally; without calibration, conclusions
  are directional only.
- This is scenario simulation, not causal identification: a change after varying a parameter is not
  a causal effect of a real intervention.
- Individual prediction, profiling or scoring is outside the model's promises and violates product
  red lines.
