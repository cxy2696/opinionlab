# Conformance: equations, code, tests

**Applies to:** OpinionLab v1.4.0 · [Docs index](README.md) ·
[Changelog](../CHANGELOG.md)

This note is the bridge between the model described in
[`MATH_MODEL.md`](MATH_MODEL.md) and the code that runs it. It lists where each
formula lives, which test checks it, and which numerical values are shared with
the HNL research repository. The fixture is also used by the
[HNL repository](https://github.com/cxy2696/Hypergraph-Nonlinear-Latency-Voter-Model).

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
| censored consensus interval | `mc.py::censored_interval` | `tests/test_censored_interval.py` |
| browser conformity map parity | `site/sim.js::conformity` | `tests/test_browser_sim_math.py` |

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

The hosted browser preview is not part of the HNL fixture, but its conformity
map is pinned to `core/kernel.py` by a separate test that runs `sim.js` under
Node and compares a grid of `(ones, zeros, q)` cases with the Python kernel.

## Reproducing the check

```bash
uv run pytest tests/test_conformance.py tests/test_kernel_math.py
uv run pytest
```

The focused files are
[`tests/test_conformance.py`](../tests/test_conformance.py) and
[`tests/test_kernel_math.py`](../tests/test_kernel_math.py). The full suite
also covers the engine equivalence, weights, decision rules and service layer.

If a deliberate model change invalidates the fixture, change the equations and
the fixture together, and explain why in the commit message. Do not regenerate
the fixture from the code; that would only test that the code agrees with
itself.

## Related documents

- [Math model](MATH_MODEL.md): the normative equations behind this map.
- [Case study](CASE_STUDY.md): the same formulas on a fragmented real-data graph.
- [Architecture](ARCHITECTURE.md): where the kernels sit in the service stack.
