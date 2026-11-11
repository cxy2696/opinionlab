#!/usr/bin/env python3
"""Run a real published hashtag graph through the engine.

The input is the CC0 Kaggle sample in ``data/kaggle_sentiment.csv``. The case
is a structural scenario: it asks what the hashtag graph and the mapped
sentiment imply for group-level absorption, not what a real population did.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from hnle.core.sparse import run_sparse
from hnle.graph import connected_components
from hnle.ingest import IngestConfig, ingest_csv
from hnle.io.manifest import save_graph
from hnle.mc import run_monte_carlo
from hnle.metrics import summarize
from hnle.spec import ModelSpec

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data" / "kaggle_sentiment.csv"
MAPPING = ROOT / "scenarios" / "mappings" / "kaggle_valence.yaml"
OUT = ROOT / "runs" / "kaggle_case"


def main() -> int:
    config = IngestConfig(
        user_column="User",
        hashtags_column="Hashtags",
        sentiment_column="Sentiment",
        engagement_column="engagement",
        mapping_path=MAPPING,
        unmapped_policy="drop",
        allow_content=True,
    )
    bundle = ingest_csv(CSV, salt=b"opinionlab-public-case-v1", config=config)
    graph = bundle.graph
    components = connected_components(graph)
    covered = {node for edge in graph.hyperedges for node in edge}
    initial = np.asarray(graph.initial_opinions or [], dtype=np.int64)

    spec = ModelSpec(
        n_steps=100,
        seed=7,
        repeats=30,
        q=1.5,
        n_opinions=2,
        init_mode="data_driven",
        weights={"source": "engagement", "normalize": "max"},
        latency={"dist": "const", "mu": 5},
        consensus_threshold=0.8,
    )
    aggregate = run_monte_carlo(spec, graph, repeats=spec.repeats, jobs=1, collect_raw=False)
    artifact = run_sparse(spec, graph, seed=spec.seed)
    summary = summarize(artifact, spec, graph.hyperedges)

    absorbed = 0
    for component in components:
        votes = artifact.opinions[component]
        absorbed += int(votes.min() == votes.max())
    ones = int(artifact.opinions.sum())
    majority = max(ones, graph.n_nodes - ones) / graph.n_nodes

    diversity = aggregate.metrics["diversity_final"]
    payload = {
        "dataset": {
            "rows": bundle.stats["row_count"],
            "sentiment_mapped_ratio": round(
                float(bundle.stats["sentiment_mapped_ratio"] or 0.0), 4
            ),
            "nodes": graph.n_nodes,
            "hyperedges": len(graph.hyperedges),
            "components": len(components),
            "largest_component": len(components[0]),
            "largest_component_share": round(len(components[0]) / graph.n_nodes, 4),
            "coverage": round(len(covered) / graph.n_nodes, 4),
            "initial_positive_share": round(float(initial.mean()), 4),
        },
        "run": {
            "q": spec.q,
            "steps": spec.n_steps,
            "repeats": spec.repeats,
            "consensus_threshold": spec.consensus_threshold,
            "diversity_final_mean": round(diversity.mean, 4),
            "diversity_final_ci95": [round(diversity.ci95_lo, 4), round(diversity.ci95_hi, 4)],
            "censored": bool(summary.time_to_consensus < 0),
            "final_majority": round(majority, 4),
            "components_absorbed": round(absorbed / len(components), 4),
        },
    }
    OUT.mkdir(parents=True, exist_ok=True)
    save_graph(OUT / "graph.npz", graph, bundle.weights)
    (OUT / "summary.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    d = payload["dataset"]
    r = payload["run"]
    print("Kaggle hashtag case")
    print(f"  rows {d['rows']}, mapped {d['sentiment_mapped_ratio']:.1%}, "
          f"nodes {d['nodes']}, edges {d['hyperedges']}")
    print(f"  components {d['components']}, largest {d['largest_component']} "
          f"({d['largest_component_share']:.1%}), coverage {d['coverage']:.1%}")
    print(f"  initial positive share {d['initial_positive_share']:.3f}")
    print(f"  final diversity {r['diversity_final_mean']:.3f} "
          f"[{r['diversity_final_ci95'][0]:.3f}, {r['diversity_final_ci95'][1]:.3f}]")
    print(f"  final majority {r['final_majority']:.3f}, "
          f"components absorbed {r['components_absorbed']:.1%}, "
          f"80% consensus {'no' if r['censored'] else 'yes'}")
    print(f"  artifacts: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
