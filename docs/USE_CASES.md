# Use cases

OpinionLab is not limited to public opinion. Any setting where **people influence each other and
opinions change** can use the same model: people become nodes, group conversations become hyperedges,
attitude shifts become adoption events, and reaction speed becomes latency.

It outputs group-level “what if” ranges, not predictions about individuals or real events.

## 1. When should we debunk a rumor?

- **Scenario:** a rumor spreads and the team can pick only one timing.
- **Template:** `s2_rumor_debunk_timing.yaml` (S2)
- **Run:** `uv run python examples/rumor_timing.py --repeats 8`
- **Read:** final positive share at T+2 / T+12 / T+24 with 95% CIs. If the CIs overlap, do not claim
  that earlier is better; add replicas or calibrate the latency distribution.
- **Output:** a comparison table plus a single-file report suitable for a review.

## 2. Will a community discussion converge or go silent?

- **Scenario:** a residents' group debates a contested issue; the facilitator wants to know whether
  light-touch guidance helps.
- **Template:** S7 (community consensus).
- **Run:** `uv run python examples/community_consensus.py --repeats 6`
- **Read:** a shorter consensus step without diversity collapsing to zero suggests genuine
  convergence. If diversity hits zero quickly, check whether conformity `q` is too high.

## 3. Communication cadence during organizational change

- **Scenario:** a company announces a restructuring in stages and fears a backlash.
- **Template:** S8 (organizational change).
- **Run:** `uv run hnle simulate --spec scenarios/s8_organizational_change.yaml --repeats 20`
- **Read:** whether cascade P99 falls while diversity stays moderate. If both worsen, stretch the
  communication window or change channels.

## 4. Word of mouth at product launch

- **Scenario:** creators and real users mix at launch; is early buzz the same as durable word of mouth?
- **Template:** S9 (product launch).
- **Read:** early cascade size is not the same as long-run diversity; watch the final negative share
  and diversity, not only the peak.

## 5. Policy and platform governance

- **Templates:** S1 (policy cadence), S3 (platform governance), S4 (brand/KOL mix).
- **Read:** post-intervention cascade distribution, consensus step and diversity; compare runs and
  check whether the difference exceeds CI noise.

## 6. Teaching and research reproduction

- **Template:** G1 (academic reproduction).
- **Run:** `uv run hnle simulate --spec scenarios/g1_academic_reproduction.yaml --repeats 20`
- **Read:** the consensus probability trend with group size at `q=1` and the spread across seeds.

## Adapting the model to your setting

1. Decide what a node is and why nodes share a hyperedge (same topic, group or meeting).
2. Estimate conformity `q`, mean latency and dispersion, and the initial stance distribution.
3. Write a `ModelSpec` YAML (copy one from `scenarios/`) and run `hnle simulate`; read the 95% CIs
   before drawing conclusions.
4. Keep assumptions, limitations and the disclaimer with the report — they matter as much as the
   numbers.
