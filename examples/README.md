# Examples

Two minimal examples using templates and the engine directly, plus a real-data case. No database or API server is needed.

## 1. Debunk timing

```bash
uv run python examples/rumor_timing.py --repeats 8
```

Compares final positive share and 95% CI for debunking at T+2, T+12 and T+24. Overlapping CIs mean
the timing effect is not established at this sample size.

## 2. Conformity in a community discussion

```bash
uv run python examples/community_consensus.py --repeats 6
```

Vary `q` and watch diversity, consensus step and absorption to distinguish genuine consensus from
conformity pressure.

## More scenarios

- `docs/USE_CASES.md`: crisis communication, community, organizational change, product launch,
  research reproduction.
- `scenarios/`: 16 templates (15 enabled; G5 is gated).
- `make demo`: interactive browser sandbox.

## Real-data case

`kaggle_hashtag_case.py` ingests `data/kaggle_sentiment.csv`, prints the graph
structure and runs the engine with 30 replicates. Run it from the repository
root with `make case` or `uv run python examples/kaggle_hashtag_case.py`. The
output and its limitations are described in `docs/CASE_STUDY.md`.
`kaggle_case.yaml` is the matching dynamics file for `hnle simulate --graph`.
