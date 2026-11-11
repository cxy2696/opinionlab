# Math model

## Formula-to-code map

| Formula | Code |
|---|---|
| `S_x(e) = Σ_{j∈e} α_j · 1(X_j=x)` | `core/update.py::edge_distributions`, `core/sparse.py::_node_probabilities` |
| `P(X_i=1|e) = S_1^q / (S_0^q + S_1^q)` | same functions (per value for multi-opinion) |
| readiness `t - T_i ≥ L_i` | `core/update.py::run_simulation` |
| node aggregation `mean / max / size_weighted` | `aggregate_node_probabilities` |
| `diversity = 1 - max_v share_v` | `metrics.diversity` |
| `entropy = -Σ p ln p` (bits in code) | `metrics.shannon_entropy` |
| oscillation: FFT peak ratio, zero crossings, lag-k autocorrelation | `metrics.fft_power_ratio`, etc. |
| `time_to_consensus`, absorbing state | `metrics.time_to_consensus`, `consensus_stability` |
| replica cost `c · nnz · steps` | `hnle/capacity.py` (measured `c ≈ 1.5e-8`) |

## Sampling vs argmax

The paper writes a deterministic `argmax_X P(X_i(t+1)=X|e)`; the upstream prototype uses
`random() < p1`. V1 exposes both explicitly:

- `decision_rule=stochastic` (default, matches the upstream dynamics),
- `decision_rule=argmax` (the paper's deterministic rule),
- `decision_rule=threshold` (switch when `p1 ≥ τ`).

Every report states the rule used, because deterministic and stochastic dynamics have different
noise properties.

## Latency and updates

- Discrete kernel: a node updates only when `t - last_change_time[i] ≥ L_i`; writes are atomic at
  the end of a step.
- Event kernel: each evaluation reschedules the node by `L_i` (heap for continuous time, buckets for
  integer delays).
- With `L_i ≡ 1` both kernels agree step by step (`tests/test_engine_equivalence.py`).

## Numerics

- Root seed → `SeedSequence.spawn(3)` for init, latency and decision streams.
- Hyperedges are sorted before aggregation, so float summation order is fixed and permutation
  invariance can reach `atol=0`.
- Metrics use float64; tests compare with `numpy.testing.assert_allclose`, never `==`.
