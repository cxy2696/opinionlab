"""hnle command line interface (typer).

The real subcommands (ingest/simulate/sweep/calibrate/compare/report/validate)
land in US-013; this entry point only wires the executable in US-001.
"""

from __future__ import annotations

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


def main() -> None:
    """Console-script entry point."""
    app()


if __name__ == "__main__":
    main()
