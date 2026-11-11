# Examples

Two minimal examples using templates and the engine directly; no database or API server needed.

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

- `docs/USE_CASES_en.md`: crisis communication, community, organizational change, product launch,
  research reproduction.
- `scenarios/`: 15 runnable templates.
- `make demo`: interactive browser sandbox.
