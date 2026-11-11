"""The real-data case stays runnable and its graph stays fragmented."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from typer.testing import CliRunner

from hnle.cli import app
from hnle.graph import Hypergraph, connected_components
from hnle.ingest import IngestConfig, ingest_csv
from hnle.io.manifest import save_graph

ROOT = Path(__file__).parents[1]
CSV = ROOT / "data" / "kaggle_sentiment.csv"
MAPPING = ROOT / "scenarios" / "mappings" / "kaggle_valence.yaml"


def test_kaggle_sample_ingests_to_a_fragmented_graph() -> None:
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
    assert bundle.stats["row_count"] == 732
    assert bundle.stats["edge_count"] == len(bundle.graph.hyperedges)
    assert bundle.graph.n_nodes > 500
    assert len(connected_components(bundle.graph)) > 50
    assert bundle.graph.initial_opinions is not None
    assert 0.5 < float(np.mean(bundle.graph.initial_opinions)) < 0.9


def test_simulate_cli_accepts_an_ingested_graph(tmp_path: Path) -> None:
    graph = Hypergraph(
        n_nodes=30,
        hyperedges=tuple((i, i + 1) for i in range(29)),
        initial_opinions=tuple(i % 2 for i in range(30)),
        weights=tuple(1.0 for _ in range(30)),
    )
    graph_path = tmp_path / "graph.npz"
    save_graph(graph_path, graph, np.ones(30, dtype=np.float64))
    scenario = tmp_path / "scenario.yaml"
    scenario.write_text(
        "spec:\n"
        "  n_steps: 5\n"
        "  seed: 1\n"
        "  repeats: 2\n"
        "  q: 1.0\n"
        "  init_mode: data_driven\n"
        "  weights:\n"
        "    source: engagement\n"
        "  latency:\n"
        "    dist: const\n"
        "    mu: 1\n",
        encoding="utf-8",
    )
    out = tmp_path / "runs"
    result = CliRunner().invoke(
        app,
        [
            "simulate",
            "--spec",
            str(scenario),
            "--graph",
            str(graph_path),
            "--out-dir",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    assert any((run / "manifest.json").exists() for run in out.iterdir())
