"""Artifact export: parquet metrics, series CSV, PNG figure and bilingual HTML.

matplotlib is forced to the Agg backend before pyplot is imported so the engine
can run on headless workers (no ``plt.show()`` anywhere).
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from hnle.core.update import RunResult  # noqa: E402
from hnle.graph import Hypergraph  # noqa: E402
from hnle.io.manifest import (  # noqa: E402
    build_manifest,
    run_id_for,
    save_graph,
    write_manifest,
)
from hnle.io.report import render_report  # noqa: E402
from hnle.metrics import summarize  # noqa: E402
from hnle.spec import ModelSpec  # noqa: E402

DISCLAIMER_ZH = "本结果为基于给定假设的情景推演，非对真实舆情的预测。"
DISCLAIMER_EN = (
    "This result is a scenario simulation under stated assumptions, "
    "not a prediction of real public opinion."
)


def series_frame(result: RunResult) -> pd.DataFrame:
    steps = np.arange(len(result.diversity_series))
    cascade = np.concatenate([[0.0], np.asarray(result.cascade_series, dtype=np.float64)])
    return pd.DataFrame(
        {
            "step": steps,
            "diversity": np.asarray(result.diversity_series, dtype=np.float64),
            "cascade": cascade,
            "mean_opinion": np.asarray(result.mean_opinion_series, dtype=np.float64),
        }
    )


def export_run(
    spec: ModelSpec,
    graph: Hypergraph,
    result: RunResult,
    out_dir: str | Path,
    *,
    weights: Any = None,
    wall_clock_seconds: float | None = None,
    include_figure: bool = True,
    aggregate: Any = None,
    narrative: dict[str, str] | None = None,
    disclaimer_key: str = "simulation_not_prediction",
    nonce: str | None = None,
) -> dict[str, Path]:
    """Write every artifact for one run into ``out_dir/<run_id>/``."""
    run_id = run_id_for(spec)
    target = Path(out_dir) / run_id
    target.mkdir(parents=True, exist_ok=True)

    frame = series_frame(result)
    series_path = target / f"{run_id}.series.csv"
    frame.to_csv(series_path, index=False, float_format="%.17g")

    summary = summarize(result, spec, graph.hyperedges).to_dict()
    metrics_frame = pd.DataFrame(
        [{"run_id": run_id, "metric": k, "value": v} for k, v in summary.items()]
    )
    metrics_path = target / f"{run_id}.metrics.parquet"
    metrics_frame.to_parquet(metrics_path, index=False)

    figure_path: Path | None = None
    if include_figure:
        figure_path = target / f"{run_id}.figure.png"
        fig, ax = plt.subplots(figsize=(7, 3.5))
        ax.plot(frame["step"], frame["diversity"], color="#2b6cb0")
        ax.set_xlabel("step")
        ax.set_ylabel("diversity")
        ax.set_title(f"OpinionLab {run_id}")
        fig.tight_layout()
        fig.savefig(figure_path, dpi=120)
        plt.close(fig)

    report_path = target / f"{run_id}.report.html"

    actual_weights = weights if weights is not None else np.ones(graph.n_nodes, dtype=np.float64)
    graph_path = save_graph(target / "graph.npz", graph, actual_weights)
    elapsed = wall_clock_seconds if wall_clock_seconds is not None else 0.0
    artifacts = {
        "series_csv": series_path.name,
        "metrics_parquet": metrics_path.name,
        "report_html": report_path.name,
        "graph_npz": graph_path.name,
    }
    if figure_path is not None:
        artifacts["figure_png"] = figure_path.name
    manifest = build_manifest(
        spec, graph, actual_weights, wall_clock_seconds=elapsed, artifacts=artifacts
    )
    report_html = render_report(
        run_id=run_id,
        spec=spec,
        summary=summary,
        frame=frame,
        manifest=manifest,
        aggregate=aggregate,
        disclaimer_key=disclaimer_key,
        narrative=narrative,
        nonce=nonce,
    )
    report_path.write_text(report_html, encoding="utf-8")
    manifest_path = write_manifest(target / "manifest.json", manifest)

    return {
        "run_id": Path(run_id),
        "manifest": manifest_path,
        "series": series_path,
        "metrics": metrics_path,
        "report": report_path,
        "graph": graph_path,
        **({"figure": figure_path} if figure_path is not None else {}),
    }


def time_run(spec: ModelSpec, graph: Hypergraph, seed: int) -> tuple[RunResult, float]:
    """Run one replica and return it with its wall-clock duration."""
    from hnle.engine import run_engine

    started = time.perf_counter()
    result = run_engine(spec, graph, seed)
    return result, time.perf_counter() - started
