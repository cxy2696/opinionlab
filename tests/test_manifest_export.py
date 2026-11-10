"""US-012: manifests, artifact export and offline reproduction."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from typer.testing import CliRunner

from hnle.cli import app
from hnle.core.sparse import run_sparse
from hnle.graph import Hypergraph, random_hypergraph
from hnle.io.export import export_run, series_frame
from hnle.io.manifest import load_manifest, reproduce, run_id_for
from hnle.spec import ModelSpec


def _case() -> tuple[ModelSpec, Hypergraph]:
    spec = ModelSpec(n_steps=40, seed=9, q=1.5, latency={"dist": "const", "mu": 1})
    graph = random_hypergraph(40, 80, np.random.default_rng(9), spec.hyperedge)
    return spec, graph


def test_manifest_has_provenance_fields(tmp_path: Path) -> None:
    spec, graph = _case()
    result = run_sparse(spec, graph, spec.seed)
    paths = export_run(spec, graph, result, tmp_path, wall_clock_seconds=0.5)
    manifest = load_manifest(paths["manifest"])
    for key in (
        "run_id",
        "config_sha256",
        "data_sha256",
        "git_sha",
        "versions",
        "seed",
        "repeats",
        "engine_version",
        "wall_clock_seconds",
        "cpu_count",
    ):
        assert key in manifest
    assert manifest["run_id"] == run_id_for(spec)
    assert manifest["versions"]["numpy"] == np.__version__
    assert len(manifest["config_sha256"]) == 64


def test_run_id_is_derived_from_config_and_seed() -> None:
    spec = ModelSpec(seed=9)
    assert run_id_for(spec) == run_id_for(spec)
    assert run_id_for(spec) != run_id_for(spec.model_copy(update={"seed": 10}))
    assert run_id_for(spec) != run_id_for(spec.model_copy(update={"q": 2.0}))


def test_export_writes_named_artifacts(tmp_path: Path) -> None:
    spec, graph = _case()
    result = run_sparse(spec, graph, spec.seed)
    paths = export_run(spec, graph, result, tmp_path)
    run_id = run_id_for(spec)
    assert paths["report"].name == f"{run_id}.report.html"
    assert paths["series"].name == f"{run_id}.series.csv"
    assert paths["metrics"].name == f"{run_id}.metrics.parquet"

    frame = pd.read_csv(paths["series"])
    assert len(frame) == spec.n_steps + 1
    assert list(frame.columns) == ["step", "diversity", "cascade", "mean_opinion"]
    metrics = pd.read_parquet(paths["metrics"])
    assert set(metrics["metric"]) >= {"diversity_final", "absorbing", "cascade_p99"}
    html = paths["report"].read_text(encoding="utf-8")
    assert "非对真实舆情的预测" in html
    assert "not a prediction" in html
    assert run_id in html


def test_reproduction_is_bitwise_identical(tmp_path: Path) -> None:
    spec, graph = _case()
    result = run_sparse(spec, graph, spec.seed)
    paths = export_run(spec, graph, result, tmp_path)
    rebuilt, rebuilt_spec = reproduce(paths["manifest"])
    assert rebuilt_spec.seed == spec.seed
    np.testing.assert_array_equal(rebuilt.opinions, result.opinions)
    np.testing.assert_allclose(rebuilt.diversity_series, result.diversity_series, atol=0.0)
    np.testing.assert_allclose(rebuilt.cascade_series, result.cascade_series, atol=0.0)
    np.testing.assert_allclose(
        series_frame(rebuilt)["mean_opinion"].to_numpy(),
        series_frame(result)["mean_opinion"].to_numpy(),
        atol=0.0,
    )


def test_cli_report_verifies_curves(tmp_path: Path) -> None:
    spec, graph = _case()
    result = run_sparse(spec, graph, spec.seed)
    export_run(spec, graph, result, tmp_path)
    run_id = run_id_for(spec)
    cli = CliRunner()
    outcome = cli.invoke(app, ["report", "--run-id", run_id, "--runs-dir", str(tmp_path)])
    assert outcome.exit_code == 0, outcome.output
    assert "verified" in outcome.output


def test_cli_report_rejects_unknown_run(tmp_path: Path) -> None:
    outcome = CliRunner().invoke(
        app, ["report", "--run-id", "missing", "--runs-dir", str(tmp_path)]
    )
    assert outcome.exit_code == 2


def test_hundred_headless_exports(tmp_path: Path) -> None:
    for index in range(100):
        spec = ModelSpec(n_steps=3, seed=index, latency={"dist": "const", "mu": 1})
        graph = Hypergraph(
            n_nodes=10,
            hyperedges=tuple((i, i + 1) for i in range(9)),
            initial_opinions=tuple(i % 2 for i in range(10)),
        )
        result = run_sparse(spec, graph, spec.seed)
        export_run(spec, graph, result, tmp_path / "batch", include_figure=index % 10 == 0)
    assert len(list((tmp_path / "batch").iterdir())) == 100
    manifest = json.loads(next((tmp_path / "batch").glob("*/manifest.json")).read_text())
    assert manifest["run_id"]


def test_source_never_calls_plt_show() -> None:
    import re

    root = Path(__file__).parents[1] / "packages" / "hnle" / "src" / "hnle"
    call = re.compile(r"^\s*plt\.show\(", re.MULTILINE)
    for path in root.rglob("*.py"):
        assert not call.search(path.read_text(encoding="utf-8")), path
