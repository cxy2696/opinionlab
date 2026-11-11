# Case study: a published hashtag sample

This case exists to show the engine on a real, citable input rather than a
synthetic template. It also shows where a population-level number stops being
useful.

## Input

`data/kaggle_sentiment.csv` is the 732-row Kaggle *Social Media Sentiments
Analysis Dataset* (CC0). The file keeps the original `User`, `Hashtags`,
`Sentiment`, `Retweets` and `Likes` columns and adds `engagement = Retweets +
Likes`. The provenance, hash and limits are in [`data/README.md`](../data/README.md).

The ingest step normalises the 191 emotion labels with
[`scenarios/mappings/kaggle_valence.yaml`](../scenarios/mappings/kaggle_valence.yaml),
maps 169 of them to positive or negative, and drops the 22 ambiguous labels.
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

The command writes `runs/kaggle_case/kaggle_sentiment.npz` and a stats file.
The same graph is produced by the example script below.

## What the graph looks like

| quantity | value |
|---|---:|
| posts | 732 |
| posts with a mapped label | 85.9 % |
| users (nodes) | 586 |
| hashtag hyperedges | 149 |
| connected components | 239 |
| largest component | 83 nodes (14.2 %) |
| nodes covered by a hyperedge | 72.7 % |
| initial positive share | 0.703 |

The graph is fragmented. The largest component is only 14 % of the population,
and 27 % of the nodes have no hyperedge at all. Under the binary model, each
component absorbs internally; the population as a whole does not.

## What the run shows

```bash
make case
```

The script uses `q=1.5`, a fixed latency of five sweeps, 100 sweeps, and 30
replicates. It seeds the opinions from the mapped sentiment and weights nodes
by engagement.

| metric | value |
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
case demonstrates the engine's input path, the component diagnostic, and the
honest reading of a censored run. It does not validate the model on social
media.

If a decision requires a population-level estimate, the graph needs bridging
interactions or a connected subgraph with a defined target. If the decision is
about groups, the component-level absorption table is the right output.

## Artifacts

`make case` writes `runs/kaggle_case/graph.npz` and
`runs/kaggle_case/summary.json`. The graph can be passed back to the CLI:

```bash
uv run hnle simulate \
  --spec examples/kaggle_case.yaml \
  --graph runs/kaggle_case/graph.npz \
  --repeats 30
```

The scenario file still controls the dynamics; the graph file supplies the
nodes, edges, initial opinions and weights. `examples/kaggle_case.yaml` sets
`weights.source: engagement` so the ingested weights are used.
