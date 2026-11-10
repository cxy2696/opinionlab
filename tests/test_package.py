"""Toolchain smoke test: the hnle package and its CLI entry point are wired."""

from typer.testing import CliRunner

import hnle
from hnle.cli import app


def test_version_is_exposed() -> None:
    assert hnle.__version__


def test_cli_version() -> None:
    result = CliRunner().invoke(app, ["version"])
    assert result.exit_code == 0, result.output
    assert "hnle" in result.output
