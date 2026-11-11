# Conformance: equations, code, tests

This note is the bridge between the model described in
[`MATH_MODEL.md`](MATH_MODEL.md) and the code that runs it. It lists where each
formula lives, which test checks it, and which numerical values are shared with
the HNL research repository.

## Formula-to-code map

| formula | code | test |
|---|---|---|
| `S_x(e) = Σ α_j 1[X_j=x]` | `core/update.py::edge_distributions`, `core/sparse.py::_node_probabilities` | `tests/test_update.py`, `tests/test_weights.py` |
| `p_v(e) = S_v^q / Σ S_u^q` | `core/kernel.py::conformity_probabilities` | `tests/test_kernel_math.py` |
| node aggregation `mean / max / size_weighted` | `core/update.py::aggregate_node_probabilities`, `core/kernel.py::normalize_rows` | `tests/test_update.py`, `tests/test_engine_equivalence.py` |
| readiness `t − T_i ≥ L_i` | `core/update.py::run_simulation`, `core/event.py::run_event` | `tests/test_update.py`, `tests/test_engine_equivalence.py` |
| threshold rule | `core/update.py::choose_opinions` | `tests/test_decision_rules.py` |
| consensus / censoring | `core/kernel.py::reached_consensus`, `metrics.time_to_consensus` | `tests/test_metrics_analytic.py` |
| Monte Carlo interval | `mc.py` | `tests/test_aggregate_ci.py` |

Two details are easy to get wrong and are therefore tested explicitly:

- the `max` aggregation is renormalised row-wise, because an element-wise
  maximum of distributions is not a distribution;
- the threshold rule keeps the current stance on a tie and only switches to a
  strictly more likely stance that reaches the threshold.

## Shared fixture

[`conformance/binary_case.json`](../conformance/binary_case.json) contains three
small binary cases. The same file is stored in the
[HNL research repository](https://github.com/cxy2696/Hypergraph-Nonlinear-Latency-Voter-Model/blob/main/conformance/binary_case.json)
and checked by both implementations. The expected values are computed from the
equations, not recorded from a run.

The cases are:

1. `binary_q1p5_mean`: five nodes, three overlapping edges, unequal weights,
   `q=1.5`.
2. `binary_q1_mean`: one edge, unequal weights, `q=1`; the kernel reduces to
   the weighted share.
3. `binary_q2_mean`: four nodes, uniform weights, `q=2`; majority amplification.

`tests/test_conformance.py` runs the cases through this repository's
`edge_distributions` and `aggregate_node_probabilities`. The HNL repository runs
the same cases through its own kernel. If the shared part of the model drifts,
both tests fail.

## What the fixture does not cover

The fixture deliberately covers only the shared subset: binary opinions,
positive weights, mean aggregation, one synchronous step. Multi-stance
opinions, the event kernel, continuous latency, shocks, interventions,
time-varying topology and the service layer are tested by repository-specific
tests, not by the shared fixture.

## Reproducing the check

```bash
python -m pytest tests/test_conformance.py tests/test_kernel_math.py
python -m pytest
```

If a deliberate model change invalidates the fixture, change the equations and
the fixture together, and explain why in the commit message. Do not regenerate
the fixture from the code; that would only test that the code agrees with
itself.
