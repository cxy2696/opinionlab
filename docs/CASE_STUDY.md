# Case study: a published hashtag sample

**Applies to:** OpinionLab v1.4.0 · [Docs index](README.md) ·
[Changelog](../CHANGELOG.md)

This case shows the engine on a real, citable input rather than a synthetic
template. It also shows where a population-level number stops being useful.
The source file, licence and hash are documented in
[`data/README.md`](../data/README.md).

## Input

`data/kaggle_sentiment.csv` is the 732-row Kaggle *Social Media Sentiments
Analysis Dataset* (CC0). The file keeps the original `User`, `Hashtags`,
`Sentiment`, `Retweets` and `Likes` columns and adds
`engagement = Retweets + Likes`.

The ingest step normalises the 191 emotion labels with
[`scenarios/mappings/kaggle_valence.yaml`](../scenarios/mappings/kaggle_valence.yaml),
maps 169 of them to positive or negative, and drops the 22 unmapped labels.
It hashes user identifiers with a fixed public salt and builds one hyperedge
per hashtag.

```bash
uv run hnle ingest \
  --csv data/kaggle_sentiment.csv \
  --org-salt opinionlab-public-case-v1 \
  --user-column User --hashtags-column Hashtags \
  --sentiment-column Sentiment --engagement-column engagement \
  --mapping scenarios/mappings/kaggle_valence.yaml \
  --allow-content \
  --out-dir runs/kaggle_case
```

The ingest command writes `runs/kaggle_case/kaggle_sentiment.npz` and
`runs/kaggle_case/kaggle_sentiment.stats.json`. The graph is the filtered
model graph: 586 nodes after label filtering, from 670 raw user handles in the
CSV. The helper script below writes a copy as `runs/kaggle_case/graph.npz`.

## What the graph looks like

| Quantity | Value |
|---|---:|
| posts | 732 |
| raw user handles | 670 |
| posts with a mapped label | 85.9 % |
| users (model nodes) | 586 |
| hashtag hyperedges | 149 |
| connected components | 239 |
| largest component | 83 nodes (14.2 %) |
| nodes covered by a hyperedge | 72.7 % |
| initial positive share | 0.703 |

The graph is fragmented. The largest component is only 14 % of the population,
and 27 % of the nodes have no hyperedge at all. Under the binary model, each
component absorbs internally; the population as a whole does not.

## What the run shows

Run the complete case, including graph construction, component diagnostics and
30 replicates:

```bash
make case
```

The script uses `q=1.5`, a fixed latency of five sweeps, 100 sweeps and 30
replicates. It seeds opinions from the mapped sentiment and weights nodes by
engagement. The matching dynamics file is
[`examples/kaggle_case.yaml`](../examples/kaggle_case.yaml); the runner is
[`examples/kaggle_hashtag_case.py`](../examples/kaggle_hashtag_case.py).

| Metric | Value |
|---|---:|
| final diversity, mean | 0.293 |
| final diversity, 95 % CI | [0.285, 0.301] |
| final majority | 0.744 |
| components internally unanimous | 100 % |
| runs reaching 80 % majority | 0 |

The last two rows are the point. Every component froze, but the global majority
stayed at 74 %, below the 80 % threshold. Raising `q` does not fix this: it
makes the components freeze faster, not agree with each other. The 80 % target
is a property of the component structure, not of the opinion dynamics alone.

## What this case is not

It is not a forecast about the platforms, the users, or the period covered by
the sample. The dataset has no per-user opinion trajectory, the user handles are
pseudonymous, and the valence mapping is a documented modelling choice. The
case demonstrates the engine's input path, the component diagnostic and the
honest reading of a censored run. It does not validate the model on social
media.

If a decision requires a population-level estimate, the graph needs bridging
interactions or a connected subgraph with a defined target. If the decision is
about groups, the component-level absorption table is the right output.

## Artifacts

`make case` writes:

- `runs/kaggle_case/graph.npz` — the ingested graph and engagement weights.
- `runs/kaggle_case/summary.json` — the dataset and run summary shown above.

The graph can be passed back to the CLI:

```bash
uv run hnle simulate \
  --spec examples/kaggle_case.yaml \
  --graph runs/kaggle_case/graph.npz \
  --repeats 30
```

The scenario file still controls the dynamics; the graph file supplies the
nodes, edges, initial opinions and weights. `examples/kaggle_case.yaml` sets
`weights.source: engagement` so the ingested weights are used.

The CSV-ingest path follows the same provenance contract as other datasets:
[`COMPLIANCE.md`](COMPLIANCE.md) covers pseudonymisation, retention and
deletion, and [`MODEL_CARD.md`](MODEL_CARD.md) covers prohibited uses.

## Related documents

- [Data sample](../data/README.md): source, hash and included-file limits.
- [Use cases](USE_CASES.md): the decision questions the engine is designed for.
- [Math model](MATH_MODEL.md): why a fragmented graph can absorb internally
  without a population-level majority.
- [Demo](DEMO.md): a browser view of the same class of scenario.
