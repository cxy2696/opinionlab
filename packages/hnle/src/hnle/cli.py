"""hnle command line interface (typer).

Every model parameter comes from :class:`hnle.spec.ModelSpec`; CLI flags and
``--set a.b=value`` overrides are merged into that single source of truth and
validated before any engine work starts.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd
import typer
import yaml  # type: ignore[import-untyped]
from pydantic import ValidationError

from hnle import __version__
from hnle.core.sparse import run_sparse
from hnle.graph import Hypergraph, random_hypergraph
from hnle.ingest import IngestConfig, IngestError, ingest_csv
from hnle.io.export import export_run, series_frame
from hnle.io.manifest import reproduce
from hnle.io.scenario import load_scenario
from hnle.mc import run_monte_carlo
from hnle.metrics import summarize
from hnle.spec import ModelSpec

app = typer.Typer(add_completion=False, no_args_is_help=True)

DEFAULT_SPEC = Path("scenarios/cn_rumor_debon_timing.yaml")


@app.callback()
def root() -> None:
    """OpinionLab simulation engine / 舆情演化仿真引擎."""


@app.command()
def version() -> None:
    """Print the hnle version. / 打印 hnle 版本。"""
    typer.echo(f"hnle {__version__}")


def _deep_set(payload: dict[str, Any], dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    cursor = payload
    for part in parts[:-1]:
        nested = cursor.get(part)
        if not isinstance(nested, dict):
            nested = {}
            cursor[part] = nested
        cursor = nested
    cursor[parts[-1]] = value


def _apply_overrides(payload: dict[str, Any], overrides: list[str]) -> dict[str, Any]:
    merged = json.loads(json.dumps(payload))
    for item in overrides:
        key, separator, raw = item.partition("=")
        if not separator or not key:
            raise typer.BadParameter(f"--set expects key=value, got {item!r}")
        try:
            value = yaml.safe_load(raw)
        except yaml.YAMLError as exc:  # pragma: no cover - defensive
            raise typer.BadParameter(f"invalid value for {key}: {raw!r}") from exc
        _deep_set(merged, key.strip(), value)
    return dict(merged)


def _report_validation_error(exc: ValidationError) -> None:
    for error in exc.errors():
        location = ".".join(str(part) for part in error["loc"]) or "<root>"
        constraint = error.get("ctx") or {}
        typer.echo(
            f"{location}: {error['msg']} | constraint={constraint} | actual={error['input']!r}",
            err=True,
        )
    raise typer.Exit(code=1)


def _load_spec(
    spec_path: Path,
    overrides: list[str],
    *,
    repeats: int | None = None,
    jobs: int | None = None,
    init_mode: str | None = None,
    decision_rule: str | None = None,
) -> tuple[ModelSpec, Hypergraph, dict[str, Any]]:
    if not spec_path.exists():
        typer.echo(f"spec not found: {spec_path}", err=True)
        raise typer.Exit(code=2)
    raw: Any = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    spec_data = raw.get("spec", raw) if isinstance(raw, dict) else raw
    merged = _apply_overrides(spec_data, overrides)
    if repeats is not None:
        merged["repeats"] = repeats
    if init_mode is not None:
        merged["init_mode"] = init_mode
    if decision_rule is not None:
        merged["decision_rule"] = decision_rule
    try:
        spec = ModelSpec.model_validate(merged)
    except ValidationError as exc:
        _report_validation_error(exc)
    graph_data = raw.get("graph") if isinstance(raw, dict) else None
    if graph_data:
        n_nodes = int(graph_data.get("n_nodes", 200))
        n_edges = int(graph_data.get("n_edges", 400))
        graph_seed = int(graph_data.get("seed", spec.seed))
        rng = np.random.default_rng(graph_seed)
        initial = graph_data.get("initial_opinions")
        if initial is not None:
            graph = Hypergraph(
                n_nodes=len(initial),
                hyperedges=random_hypergraph(
                    len(initial), n_edges, rng, spec.hyperedge
                ).hyperedges,
                initial_opinions=tuple(int(value) for value in initial),
            )
        else:
            graph = random_hypergraph(n_nodes, n_edges, rng, spec.hyperedge)
        return spec, graph, graph_data
    rng = np.random.default_rng(spec.seed)
    return spec, random_hypergraph(200, 400, rng, spec.hyperedge), {}


@app.command()
def validate(
    spec: Path = typer.Option(..., "--spec", help="Scenario file / 场景文件"),
) -> None:
    """Validate a scenario or spec file without running it."""
    try:
        parsed, graph, _ = load_scenario(spec)
    except ValidationError as exc:
        _report_validation_error(exc)
    except (OSError, ValueError) as exc:
        typer.echo(f"invalid scenario: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(
        f"OK: spec valid, {graph.n_nodes} nodes / {len(graph.hyperedges)} edges, "
        f"seed={parsed.seed}, repeats={parsed.repeats}"
    )


@app.command()
def simulate(
    spec: Path = typer.Option(DEFAULT_SPEC, "--spec", help="Scenario file / 场景文件"),
    set_values: list[str] = typer.Option(
        [], "--set", help="Override e.g. --set q=2.0 --set latency.dist=exponential"
    ),
    repeats: Optional[int] = typer.Option(
        None, help="Monte-Carlo replicas / 副本数 (default: spec)"
    ),
    jobs: int = typer.Option(1, help="Parallel workers / 并行进程数"),
    max_memory_gb: Optional[float] = typer.Option(
        None, help="Raw-curve memory cap / 内存上限"
    ),
    init_mode: Optional[str] = typer.Option(None, help="data_driven|balanced_random|fixed_ratio"),
    decision_rule: Optional[str] = typer.Option(None, help="stochastic|argmax|threshold"),
    out_dir: Path = typer.Option(Path("runs"), help="Artifact root / 产物目录"),
) -> None:
    """Run one scenario (Monte-Carlo when repeats > 1) and export artifacts."""
    parsed, graph, _graph_data = _load_spec(
        spec, set_values, repeats=repeats, init_mode=init_mode, decision_rule=decision_rule
    )
    started = time.perf_counter()
    aggregate = run_monte_carlo(
        parsed,
        graph,
        repeats=parsed.repeats,
        jobs=jobs,
        collect_raw=False,
        max_memory_gb=max_memory_gb,
    )
    elapsed = time.perf_counter() - started

    # The reproducible artifact run uses spec.seed itself, so `hnle report`
    # can rebuild it exactly from the manifest.
    artifact_started = time.perf_counter()
    artifact = run_sparse(parsed, graph, parsed.seed)
    artifact_elapsed = time.perf_counter() - artifact_started
    paths = export_run(
        parsed, graph, artifact, out_dir,
        wall_clock_seconds=artifact_elapsed, include_figure=True,
    )
    metrics = summarize(artifact, parsed, graph.hyperedges).to_dict()
    diversity = aggregate.metrics["diversity_final"]
    typer.echo(
        f"run {paths['run_id']} · {parsed.repeats} replicas in {elapsed:.2f}s\n"
        f"diversity mean={diversity.mean:.4f} ci95=[{diversity.ci95_lo:.4f}, "
        f"{diversity.ci95_hi:.4f}] · absorbing={metrics['absorbing']}\n"
        f"artifacts: {out_dir / paths['run_id']}"
    )


@app.command()
def ingest(
    csv: Path = typer.Option(..., "--csv", help="UTF-8 CSV file / 输入 CSV"),
    org_salt: Optional[str] = typer.Option(None, help="Per-org HMAC salt / 每 org 盐"),
    out_dir: Path = typer.Option(Path("datasets"), help="Output directory / 输出目录"),
    mapping: Optional[Path] = typer.Option(None, help="Sentiment mapping YAML"),
    unmapped_policy: str = typer.Option("drop", help="drop|to_negative|to_positive|exclude_user"),
) -> None:
    """Pseudonymise a CSV, build a hypergraph and write a snapshot."""
    salt = org_salt or None
    if salt is None:
        typer.echo("--org-salt (or PSEUDONYM_HMAC_KEY) is required", err=True)
        raise typer.Exit(code=2)
    config = IngestConfig(mapping_path=mapping, unmapped_policy=unmapped_policy)
    try:
        result = ingest_csv(csv, salt=salt.encode("utf-8"), config=config)
    except IngestError as exc:
        typer.echo(f"{exc.code}: {exc.message} {exc.details}", err=True)
        raise typer.Exit(code=1) from exc
    out_dir.mkdir(parents=True, exist_ok=True)
    from hnle.io.manifest import save_graph

    target = out_dir / f"{csv.stem}.npz"
    save_graph(target, result.graph, result.weights)
    (out_dir / f"{csv.stem}.stats.json").write_text(
        json.dumps(result.stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    typer.echo(
        f"ingested {result.stats['node_count']} nodes / "
        f"{result.stats['edge_count']} edges → {target}"
    )


def _grid_combos(grid: list[str]) -> list[dict[str, Any]]:
    combos: list[dict[str, Any]] = [{}]
    for item in grid:
        key, separator, raw = item.partition("=")
        if not separator:
            raise typer.BadParameter(f"--grid expects key=v1,v2, got {item!r}")
        values = [yaml.safe_load(part) for part in raw.split(",")]
        expanded: list[dict[str, Any]] = []
        for combo in combos:
            for value in values:
                candidate = json.loads(json.dumps(combo))
                _deep_set(candidate, key.strip(), value)
                expanded.append(candidate)
        combos = expanded
    return combos


@app.command()
def sweep(
    spec: Path = typer.Option(DEFAULT_SPEC, "--spec", help="Scenario file"),
    grid: list[str] = typer.Option(
        [], "--grid", help="Grid axis e.g. --grid q=1,1.5,2 --grid latency.mu=2,5"
    ),
    out: Path = typer.Option(Path("sweep.csv"), help="Sweep result CSV"),
) -> None:
    """Run a parameter grid and write one row per combination."""
    base, graph, _ = _load_spec(spec, [])
    combos = _grid_combos(grid) or [{}]
    rows: list[dict[str, Any]] = []
    for combo in combos:
        payload = base.model_dump(mode="json")
        for key, value in combo.items():
            _deep_set(payload, key, value)
        variant = ModelSpec.model_validate(payload)
        result = run_sparse(variant, graph, variant.seed)
        summary = summarize(result, variant, graph.hyperedges).to_dict()
        rows.append({**combo, "q": variant.q, **summary})
    frame = pd.DataFrame(rows)
    frame.to_csv(out, index=False)
    typer.echo(f"sweep: {len(rows)} combos → {out}")


@app.command()
def calibrate(
    spec: Path = typer.Option(DEFAULT_SPEC, "--spec", help="Scenario file"),
    target: Path = typer.Option(..., "--target", help="Target series CSV (diversity column)"),
    grid: list[str] = typer.Option([], "--grid", help="Parameter grid e.g. --grid q=1,1.5,2"),
    out: Path = typer.Option(Path("calibration.json"), help="Result JSON"),
) -> None:
    """Pick the grid point whose diversity curve is closest to a target series."""
    base, graph, _ = _load_spec(spec, [])
    frame = pd.read_csv(target)
    if "diversity" not in frame:
        typer.echo("target CSV needs a diversity column", err=True)
        raise typer.Exit(code=2)
    target_series = frame["diversity"].to_numpy(dtype=np.float64)
    best: tuple[float, dict[str, Any]] | None = None
    for combo in _grid_combos(grid) or [{}]:
        payload = base.model_dump(mode="json")
        for key, value in combo.items():
            _deep_set(payload, key, value)
        variant = ModelSpec.model_validate(payload)
        result = run_sparse(variant, graph, variant.seed)
        curve = np.asarray(result.diversity_series[: target_series.size], dtype=np.float64)
        length = min(curve.size, target_series.size)
        rmse = float(np.sqrt(np.mean((curve[:length] - target_series[:length]) ** 2)))
        if best is None or rmse < best[0]:
            best = (rmse, combo)
    assert best is not None
    payload = {"rmse": best[0], "params": best[1], "spec": base.model_dump(mode="json")}
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    typer.echo(f"best rmse={best[0]:.6f} params={best[1]} → {out}")


@app.command()
def compare(
    spec: Path = typer.Option(DEFAULT_SPEC, "--spec", help="Baseline scenario file"),
    variant: list[str] = typer.Option(
        [], "--variant", help="Variant override e.g. --variant q=2.0"
    ),
    repeats: int = typer.Option(5, help="Paired replicas / 配对副本数"),
    out: Path = typer.Option(Path("compare.json"), help="Comparison JSON"),
) -> None:
    """Compare the baseline against one or more single-override variants."""
    base, graph, _ = _load_spec(spec, [])
    seed = base.seed
    baseline = run_sparse(base.model_copy(update={"repeats": repeats}), graph, seed)
    variants: list[dict[str, Any]] = []
    for index, item in enumerate(variant):
        payload = base.model_dump(mode="json")
        key, separator, raw = item.partition("=")
        if not separator:
            raise typer.BadParameter(f"--variant expects key=value, got {item!r}")
        _deep_set(payload, key.strip(), yaml.safe_load(raw))
        candidate = ModelSpec.model_validate(payload)
        result = run_sparse(candidate, graph, seed + index + 1)
        base_div = baseline.diversity_series[-1]
        variant_div = result.diversity_series[-1]
        direction = "improved" if variant_div > base_div else "worsened"
        variants.append(
            {
                "override": item,
                "diversity_final": variant_div,
                "baseline": base_div,
                "direction": direction,
            }
        )
    out.write_text(
        json.dumps({"baseline": base.model_dump(mode="json"), "variants": variants},
                   ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    typer.echo(f"compare: {len(variants)} variants → {out}")


@app.command()
def report(
    run_id: str = typer.Option(..., help="Run id (config sha + seed) / 运行 ID"),
    runs_dir: Path = typer.Option(Path("runs"), help="Artifact root / 产物根目录"),
) -> None:
    """Rebuild a run from its manifest and verify the curves are identical."""
    manifest_path = runs_dir / run_id / "manifest.json"
    if not manifest_path.exists():
        typer.echo(f"manifest not found: {manifest_path}", err=True)
        raise typer.Exit(code=2)
    result, _spec = reproduce(manifest_path)
    rebuilt = series_frame(result)
    original = pd.read_csv(
        runs_dir / run_id / f"{run_id}.series.csv", float_precision="round_trip"
    )
    for column in ("diversity", "cascade", "mean_opinion"):
        np.testing.assert_allclose(
            rebuilt[column].to_numpy(),
            original[column].to_numpy(),
            atol=0.0,
            rtol=0.0,
            err_msg=f"rebuilt {column} differs from the stored run",
        )
    typer.echo(f"report verified: {run_id} (curves identical) / 曲线逐位一致")


def main() -> None:
    """Console-script entry point."""
    app()


if __name__ == "__main__":
    main()
