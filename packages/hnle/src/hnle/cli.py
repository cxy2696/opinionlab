"""hnle command line interface (typer).

The real subcommands (ingest/simulate/sweep/calibrate/compare/report/validate)
land in US-013; this entry point only wires the executable in US-001.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import typer

from hnle import __version__

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="OpinionLab simulation engine (hnle) / 舆情演化仿真引擎",
)


@app.callback()
def root() -> None:
    """OpinionLab simulation engine / 舆情演化仿真引擎."""


@app.command()
def version() -> None:
    """Print the hnle version. / 打印 hnle 版本。"""
    typer.echo(f"hnle {__version__}")


@app.command()
def report(
    run_id: str = typer.Option(..., help="Run id (config sha + seed) / 运行 ID"),
    runs_dir: Path = typer.Option(Path("runs"), help="Artifact root / 产物根目录"),
) -> None:
    """Rebuild a run from its manifest and verify the curves are identical."""
    from hnle.io.export import series_frame
    from hnle.io.manifest import reproduce

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
