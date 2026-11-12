# Examples

**Applies to:** OpinionLab v1.3.1 · [Docs index](../docs/README.md) ·
[Use cases](../docs/USE_CASES.md) · [Changelog](../CHANGELOG.md)

Three runnable paths use the templates and engine directly. The first two need
no database or API server; the third uses the included CC0 sample. Run commands
from the repository root after `make setup`.

## 1. Debunk timing

```bash
uv run python examples/rumor_timing.py --repeats 8
```

Compares final positive share and its 95 % CI for debunking at T+2, T+12 and
T+24 on the S2 template. Overlapping CIs mean the timing effect is not
established at this sample size. This script prints the comparison table; use
the demo’s report endpoint for a shareable HTML artifact.

## 2. Conformity in a community discussion

```bash
uv run python examples/community_consensus.py --repeats 6
```

Varies `q` on the S7 template and prints final diversity, consensus step and
absorbing rate. The point is to distinguish genuine convergence from
conformity pressure.

## 3. Real-data hashtag case

```bash
make case
# or:
uv run python examples/kaggle_hashtag_case.py
```

`kaggle_hashtag_case.py` ingests
[`data/kaggle_sentiment.csv`](../data/kaggle_sentiment.csv), prints the graph
structure and runs the engine with 30 replicates. It writes
`runs/kaggle_case/graph.npz` and `runs/kaggle_case/summary.json`. The output,
the component diagnostic and the limitations are described in
[`docs/CASE_STUDY.md`](../docs/CASE_STUDY.md).

[`kaggle_case.yaml`](kaggle_case.yaml) is the matching dynamics file for
`hnle simulate --graph`.

## More scenarios

- [`docs/USE_CASES.md`](../docs/USE_CASES.md): policy, community,
  organizational change, product launch and research reproduction.
- [`scenarios/`](../scenarios/): 16 templates (15 enabled; G5 is gated).
- [`make demo`](../Makefile): the interactive browser sandbox.

List the current templates from the CLI:

```bash
uv run hnle templates
```

## Related documents

- [Use cases](../docs/USE_CASES.md): the six worked questions behind these
  scripts.
- [Math model](../docs/MATH_MODEL.md): the estimator and censoring rules.
- [Data sample](../data/README.md): source, hash and mapping limits.
- [Demo](../docs/DEMO.md): the browser product surface.
