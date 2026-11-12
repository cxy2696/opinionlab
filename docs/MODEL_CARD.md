# Model card

**Applies to:** OpinionLab v1.3.1 · [Docs index](README.md) ·
[Changelog](../CHANGELOG.md)

## Intended use

OpinionLab supports directional, group-level scenario analysis: compare
assumptions, inspect the range produced by replicas, and communicate
uncertainty honestly. It is a simulator, not an observatory and not a
forecasting product.

## Capabilities

- Hypergraph group interaction, non-linear conformity `q`, and heterogeneous
  latency.
- Group-level metrics with 95 % confidence intervals: diversity, entropy,
  polarisation, cascade quantiles, convergence and oscillation.
- Reproducible runs with manifests and single-file offline reports.
- Two engine paths: synchronous CSR and event-driven integer latency, with
  shared kernel semantics plus repository-specific tests.
- A browser demo with English, Chinese, Japanese and German labels, 3D telemetry and linked charts;
  see [Demo](DEMO.md).

## Limitations

- Does not model recommender systems, media agenda, offline behaviour or real
  price feedback.
- Parameters and topology come from the supplied data; conclusions hold only
  inside the declared assumption space.
- Coarse parameters give directional insight, not precise forecasts.
- Population-level `absorbing`/`runaway` labels assume a connected graph. On a
  fragmented graph, components can freeze while the population flag stays
  false; inspect the component structure. The [case study](CASE_STUDY.md) is a
  worked example.
- A consensus time is censored when no majority forms in the window. Censoring
  is not evidence that the process will never converge; it bounds the claim to
  the observation window. See
  [Math model §6](MATH_MODEL.md#6-monte-carlo-estimator-and-intervals).

## Prohibited uses

- No prediction, profiling or scoring of real individuals.
- No election forecasting, targeted persuasion, or any use that violates local
  law.
- No covert monitoring or re-identification.

## Data and compliance

- Input IDs are HMAC-SHA256 pseudonymised; PII columns are rejected.
- Default retention is 180 days, with cascading dataset deletion.
- CN/EU dual-region deployment; cross-region tenant access returns
  `403 REGION_MISMATCH`.
- Reports carry the fixed disclaimer; any missing disclaimer fails the report
  gate.
- G5 election-use review and red lines are documented in
  [Compliance](COMPLIANCE.md).

## Generative content

The engine does not call generative models for metrics or conclusions. Optional
Ollama narration is disabled by default, must be explicitly enabled, is
labelled “AI-assisted explanation, not a conclusion”, and requires human review;
it changes no metric, decision or report number. The hosted demo cannot call a
local Ollama instance.

## Evaluation and provenance

- Engine equations and test mappings: [Math model](MATH_MODEL.md) and
  [Conformance](CONFORMANCE.md).
- Capacity calibration: [Capacity report](capacity-report.md).
- Operational controls and tainted-run handling: [Runbook](RUNBOOK.md).
- Input provenance for the included sample: [Data sample](../data/README.md).

## Related documents

- [Use cases](USE_CASES.md): questions this model can help frame.
- [Demo](DEMO.md): what the browser surface does and does not claim.
- [Compliance](COMPLIANCE.md): retention, deletion, regional and use-case rules.
