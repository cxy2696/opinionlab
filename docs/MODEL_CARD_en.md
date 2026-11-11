# Model card

> **In one minute**
>
> - It does: group-level what-if simulation, 95% CIs and reproducible reports.
> - It does not: individual prediction, profiling, election forecasting or targeted persuasion.
> - No generative model is used for conclusions; Ollama narration is off by default and labelled.

## Capabilities

- Hypergraph group interaction, non-linear conformity `q`, and heterogeneous latency.
- Group-level metrics with 95% confidence intervals: diversity, entropy, polarisation, cascade
  quantiles, convergence and oscillation.
- Reproducible runs with manifests and single-file offline reports.

## Limitations

- Does not model recommender systems, media agenda, offline behaviour or real price feedback.
- Parameters and topology come from the supplied data; conclusions hold only inside the declared
  assumption space.
- Coarse parameters give directional insight, not precise forecasts.

## Prohibited uses

- No prediction, profiling or scoring of real individuals.
- No election forecasting, targeted persuasion, or any use that violates local law.
- No covert monitoring or re-identification.

## Data and compliance

- Input IDs are HMAC-SHA256 pseudonymised; PII columns are rejected.
- Default retention is 180 days, with cascading dataset deletion.
- CN/EU dual-region deployment; cross-region tenant access returns 403.
- Reports carry the fixed disclaimer; any missing disclaimer fails the report gate.

## Generative content

The engine does not call generative models for metrics or conclusions. Optional Ollama narration is
disabled by default, must be explicitly enabled, is labelled “AI-assisted explanation, not a
conclusion”, and requires human review; it changes no metric, decision or report number.
