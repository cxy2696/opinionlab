# Use cases

**Applies to:** OpinionLab v1.4.0 · [Docs index](README.md) ·
[Changelog](../CHANGELOG.md)

OpinionLab is not limited to public opinion. Any setting where **people
influence each other and opinions change** can use the same model: people become
nodes, group conversations become hyperedges, attitude shifts become adoption
events, and reaction speed becomes latency.

It outputs group-level “what if” ranges, not predictions about individuals or
real events. Run the commands below from the repository root after `make setup`.

Every template now carries four extra fields that the browser and the API
surface: the **decision** it informs, a **real-world use** (the team and the
workflow), the **parameters to set first** and how to calibrate them, and the
**signal to watch** with its decision rule. The scenario brief in the demo
renders them; `uv run hnle templates` lists the library. The
[User guide](USER_GUIDE.md#scenario-library) has the full table.

## 1. When should we debunk a rumor?

- **Question:** a rumor is spreading and the team can pick only one timing.
- **Template:** [`scenarios/s2_rumor_debunk_timing.yaml`](../scenarios/s2_rumor_debunk_timing.yaml) (S2).
- **Run:**

  ```bash
  uv run python examples/rumor_timing.py --repeats 8
  ```

- **Output:** a table of final positive share at T+2, T+12 and T+24 with 95 %
  confidence intervals.
- **Read:** if the intervals overlap, do not claim that earlier is better; add
  replicas or calibrate the latency distribution. See the
  [Math model](MATH_MODEL.md#6-monte-carlo-estimator-and-intervals).
- **Share:** use the browser report in [Demo](DEMO.md) or the demo report
  endpoint when you need a single-file artifact. The example script itself only
  prints the comparison table.

## 2. Will a community discussion converge or go silent?

- **Question:** a residents' group debates a contested issue; the facilitator
  wants to know whether light-touch guidance helps.
- **Template:** [`scenarios/s7_community_consensus.yaml`](../scenarios/s7_community_consensus.yaml) (S7).
- **Run:**

  ```bash
  uv run python examples/community_consensus.py --repeats 6
  ```

- **Output:** a table of `q` values with final diversity and its 95 % interval,
  plus mean consensus step and absorbing rate.
- **Read:** a shorter consensus step without diversity collapsing to zero
  suggests genuine convergence. If diversity hits zero quickly, check whether
  conformity `q` is too high or the group is simply being flattened by a local
  majority.

## 3. Communication cadence during organizational change

- **Question:** a company announces a restructuring in stages and fears a
  backlash.
- **Template:** [`scenarios/s8_organizational_change.yaml`](../scenarios/s8_organizational_change.yaml) (S8).
- **Run:**

  ```bash
  uv run hnle simulate --spec scenarios/s8_organizational_change.yaml --repeats 20
  ```

- **Read:** whether cascade P99 falls while diversity stays moderate. If both
  worsen, stretch the communication window or change channels and rerun with one
  change at a time.

## 4. Word of mouth at product launch

- **Question:** creators and real users mix at launch; is early buzz the same as
  durable word of mouth?
- **Template:** [`scenarios/s9_product_launch.yaml`](../scenarios/s9_product_launch.yaml) (S9).
- **Run:**

  ```bash
  uv run hnle simulate --spec scenarios/s9_product_launch.yaml --repeats 20
  ```

- **Read:** early cascade size is not the same as long-run diversity. Watch the
  final negative share and diversity, not only the peak. A large early spike can
  coexist with a fragmented, low-consensus end state.

## 5. Policy and platform governance

- **Questions:** should a policy be released in stages? does platform throttling
  reduce an extreme narrative? does the creator mix change the opinion
  distribution?
- **Templates:**
  [`s1_policy_release_cadence.yaml`](../scenarios/s1_policy_release_cadence.yaml)
  (S1), [`s3_platform_governance.yaml`](../scenarios/s3_platform_governance.yaml)
  (S3) and [`s4_brand_kol_mix.yaml`](../scenarios/s4_brand_kol_mix.yaml) (S4).
- **Run:** start from S3 and adjust one timing or exposure parameter:

  ```bash
  uv run hnle simulate --spec scenarios/s3_platform_governance.yaml \
    --repeats 20 --set q=2.0
  ```

- **Read:** post-intervention cascade distribution, consensus step and
  diversity. Compare runs and check whether the difference exceeds CI noise.
- **Compare:** use `uv run hnle compare` to evaluate one parameter override
  against a baseline without losing the original spec.

## 6. Teaching and research reproduction

- **Question:** in the classical voter limit, does consensus probability decay
  with group size as expected?
- **Template:** [`scenarios/g1_academic_reproduction.yaml`](../scenarios/g1_academic_reproduction.yaml) (G1).
- **Run:**

  ```bash
  uv run hnle simulate --spec scenarios/g1_academic_reproduction.yaml --repeats 20
  ```

- **Read:** the consensus and absorbing rates at `q=1`; copy the scenario with a
  different `graph.n_nodes` and repeat to compare group sizes. The shared
  numerical contract with the HNL research repository is in
  [Conformance](CONFORMANCE.md).

## Template library

The full library has 16 templates (15 enabled; G5 is gated):

- **G1–G7:** academic reproduction, fact checking, public health, platform
  systemic risk, election research (gated), disaster warning and corporate
  change.
- **S1–S9:** policy cadence, rumor debunking, platform governance, brand/KOL
  mix, emergency science literacy, financial expectations, community consensus,
  organizational change and product launch.

List the current templates with their English/Chinese source questions:

```bash
uv run hnle templates
```

G5 is disabled by default and requires use-case review; see
[Compliance](COMPLIANCE.md#use-case-review).

## From a scenario to a real engagement

1. **Match the decision, not the label.** Pick the template whose decision
   statement matches the decision you actually have to make. S2 and G2 both
   concern corrections, but S2 is about timing around a rumor peak and G2 is
   about blocking secondary spread; the parameter advice differs.
2. **Calibrate before comparing.** Fill `q`, the latency distribution and the
   initial stance shares from observed behaviour (reply agreement, median
   response time, label shares). Without calibration the run is a directional
   what-if, and the scenario brief says so.
3. **Pre-register the primary metric and the comparison.** Decide whether the
   decision hinges on final diversity, cascade P99, majority step or a share
   before you look at the runs. Comparing every metric and picking the one that
   separates is not evidence.
4. **Use enough replicas and report the interval.** Thirty or more replicas is
   the working minimum for a decision; below that the `underpowered` flag is on
   and the interval is wide. Report the interval and the censoring rate, not
   just the mean.
5. **Change one thing at a time.** Treat the baseline as fixed, change one
   timing, parameter or exposure, and rerun with the same seed set. Use
   `hnle compare` for the paired bootstrap interval.
6. **Keep the boundary with the result.** Share the assumptions, limitations,
   the fixed disclaimer and the evidence flags. A number without them is not a
   deliverable.

## Adapting the model to your setting

1. Decide what a node is and why nodes share a hyperedge (same topic, group or
   meeting).
2. Estimate conformity `q`, mean latency and dispersion, and the initial stance
   distribution.
3. Write a `ModelSpec` YAML (copy one from [`scenarios/`](../scenarios/)) and run
   `hnle simulate`; read the 95 % CIs before drawing conclusions.
4. Keep assumptions, limitations and the disclaimer with the report — they
   matter as much as the numbers.

## Related documents

- [Demo](DEMO.md): the interactive product surface.
- [Math model](MATH_MODEL.md): the normative equations and estimators.
- [Model card](MODEL_CARD.md): product boundaries and prohibited uses.
- [Case study](CASE_STUDY.md): a real-data worked example.
- [Examples](../examples/README.md): the scripts used above.
