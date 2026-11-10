"""US-013: the typer CLI exposes every command and validates overrides."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
import pytest
from typer.testing import CliRunner

from hnle.cli import app

SCENARIO = """\
spec:
  n_steps: 10
  seed: 3
  repeats: 2
  q: 1.5
  latency:
    dist: const
    mu: 1
graph:
  n_nodes: 30
  n_edges: 60
  seed: 3
"""


@pytest.fixture
def scenario(tmp_path: Path) -> Path:
    path = tmp_path / "scenario.yaml"
    path.write_text(SCENARIO, encoding="utf-8")
    return path


def test_help_lists_all_subcommands() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("ingest", "simulate", "sweep", "calibrate", "compare", "report", "validate"):
        assert command in result.output


def test_simulate_help_lists_options_and_defaults() -> None:
    result = CliRunner().invoke(
        app, ["simulate", "--help"], env={"COLUMNS": "200", "TERM": "dumb"}
    )
    assert result.exit_code == 0
    plain = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", result.output)
    for option in (
        "--spec",
        "--set",
        "--repeats",
        "--jobs",
        "--max-memory-gb",
        "--init-mode",
        "--decision-rule",
        "--out-dir",
    ):
        assert option in plain
    assert "scenarios/cn_rumor_debon_timing.yaml" in plain


def test_simulate_runs_and_exports(scenario: Path, tmp_path: Path) -> None:
    out = tmp_path / "runs"
    result = CliRunner().invoke(
        app,
        ["simulate", "--spec", str(scenario), "--repeats", "2", "--out-dir", str(out)],
    )
    assert result.exit_code == 0, result.output
    run_dirs = list(out.iterdir())
    assert len(run_dirs) == 1
    assert (run_dirs[0] / "manifest.json").exists()


def test_set_override_changes_spec(scenario: Path, tmp_path: Path) -> None:
    out = tmp_path / "runs"
    result = CliRunner().invoke(
        app,
        [
            "simulate",
            "--spec",
            str(scenario),
            "--set",
            "q=2.0",
            "--set",
            "latency.dist=exponential",
            "--set",
            "latency.mu=5",
            "--out-dir",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    manifest = json.loads((next(out.iterdir()) / "manifest.json").read_text())
    assert manifest["spec"]["q"] == 2.0
    assert manifest["spec"]["latency"]["dist"] == "exponential"
    assert manifest["spec"]["latency"]["lambda"] == pytest.approx(1 / 5)


@pytest.mark.parametrize("bad", ["q=0", "q=abc", "n_opinions=1", "consensus_threshold=0.4"])
def test_invalid_set_override_exits_nonzero(bad: str, scenario: Path, tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app, ["simulate", "--spec", str(scenario), "--set", bad, "--out-dir", str(tmp_path)]
    )
    assert result.exit_code != 0
    field = bad.split("=")[0]
    assert field in result.output
    assert "constraint" in result.output or "actual" in result.output


def test_validate_accepts_and_rejects(scenario: Path, tmp_path: Path) -> None:
    ok = CliRunner().invoke(app, ["validate", "--spec", str(scenario)])
    assert ok.exit_code == 0
    assert "OK" in ok.output

    bad = tmp_path / "bad.yaml"
    bad.write_text("spec:\n  q: 0\n", encoding="utf-8")
    failed = CliRunner().invoke(app, ["validate", "--spec", str(bad)])
    assert failed.exit_code == 1
    assert "q" in failed.output


def test_sweep_writes_csv(scenario: Path, tmp_path: Path) -> None:
    out = tmp_path / "sweep.csv"
    result = CliRunner().invoke(
        app, ["sweep", "--spec", str(scenario), "--grid", "q=1,2", "--out", str(out)]
    )
    assert result.exit_code == 0, result.output
    frame = pd.read_csv(out)
    assert len(frame) == 2
    assert set(frame["q"]) == {1.0, 2.0}


def test_calibrate_uses_target_series(scenario: Path, tmp_path: Path) -> None:
    runs = tmp_path / "runs"
    CliRunner().invoke(
        app, ["simulate", "--spec", str(scenario), "--out-dir", str(runs)]
    )
    series = next(runs.glob("*/*.series.csv"))
    out = tmp_path / "calibration.json"
    result = CliRunner().invoke(
        app,
        [
            "calibrate",
            "--spec",
            str(scenario),
            "--target",
            str(series),
            "--grid",
            "q=1,1.5",
            "--out",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(out.read_text())
    assert "rmse" in payload and "params" in payload


def test_compare_writes_directions(scenario: Path, tmp_path: Path) -> None:
    out = tmp_path / "compare.json"
    result = CliRunner().invoke(
        app,
        [
            "compare",
            "--spec",
            str(scenario),
            "--variant",
            "q=2.0",
            "--variant",
            "q=1.0",
            "--out",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(out.read_text())
    assert len(payload["variants"]) == 2
    for item in payload["variants"]:
        assert {"metric", "baseline", "variant", "direction", "significant"} <= set(item)
        assert item["direction"].split(":")[-1] in {"improved", "worsened", "inconclusive"}


def test_ingest_writes_snapshot(tmp_path: Path) -> None:
    csv = tmp_path / "data.csv"
    pd.DataFrame(
        [
            {"user": f"u{i}", "hashtags": f"#tag{i % 3}", "sentiment": "joy"}
            for i in range(12)
        ]
    ).to_csv(csv, index=False)
    out = tmp_path / "datasets"
    result = CliRunner().invoke(
        app, ["ingest", "--csv", str(csv), "--org-salt", "s", "--out-dir", str(out)]
    )
    assert result.exit_code == 0, result.output
    assert (out / "data.npz").exists()
    stats = json.loads((out / "data.stats.json").read_text())
    assert stats["node_count"] == 12


def test_repo_scenario_and_report_roundtrip(tmp_path: Path) -> None:
    out = tmp_path / "runs"
    result = CliRunner().invoke(
        app,
        [
            "simulate",
            "--spec",
            "scenarios/cn_rumor_debon_timing.yaml",
            "--repeats",
            "1",
            "--out-dir",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    run_dir = next(out.iterdir())
    run_id = run_dir.name
    verified = CliRunner().invoke(
        app, ["report", "--run-id", run_id, "--runs-dir", str(out)]
    )
    assert verified.exit_code == 0, verified.output
