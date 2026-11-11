"""the scenario template library has 12 bilingual, runnable templates."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from hnle.cli import app
from hnle.spec import ModelSpec
from hnle.templates import iter_templates, load_template

SCENARIOS = Path(__file__).parents[1] / "scenarios"
ENABLED_KEYS = {
    "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9",
    "G1", "G2", "G3", "G4", "G6", "G7",
}


def test_enabled_templates_plus_gated_election() -> None:
    templates = iter_templates(SCENARIOS)
    enabled = {template.key for template in templates if template.is_enabled()}
    assert enabled >= ENABLED_KEYS
    gated = [template for template in templates if not template.enabled_by_default]
    assert [template.key for template in gated] == ["G5"]
    assert gated[0].is_enabled({"FF_G5_ELECTION_TEMPLATES": "1"})
    assert not gated[0].is_enabled({})


def test_every_template_has_complete_bilingual_metadata() -> None:
    for template in iter_templates(SCENARIOS):
        assert isinstance(template.spec, ModelSpec)
        for attribute in (
            "name_zh",
            "name_en",
            "question_zh",
            "question_en",
            "data_shape_zh",
            "data_shape_en",
            "interpretation_zh",
            "interpretation_en",
            "assumptions_zh",
            "assumptions_en",
            "limitations_zh",
            "limitations_en",
        ):
            assert getattr(template, attribute).strip(), (template.key, attribute)


def test_election_template_is_blocked_without_flag(tmp_path: Path) -> None:
    template = load_template(SCENARIOS / "g5_election_academic.yaml")
    result = CliRunner().invoke(
        app, ["simulate", "--spec", str(template.path), "--out-dir", str(tmp_path)]
    )
    assert result.exit_code == 3
    assert "feature flag" in result.output.lower() or "disabled" in result.output.lower()


def test_every_template_runs_and_reports_ci(tmp_path: Path) -> None:
    runner = CliRunner()
    for template in iter_templates(SCENARIOS):
        if not template.is_enabled():
            continue
        out = tmp_path / template.key
        result = runner.invoke(
            app,
            [
                "simulate",
                "--spec",
                str(template.path),
                "--set",
                "n_steps=10",
                "--repeats",
                "2",
                "--out-dir",
                str(out),
            ],
        )
        assert result.exit_code == 0, (template.key, result.output)
        report = next(out.glob("*/*.report.html"))
        html = report.read_text(encoding="utf-8")
        assert "95% CI" in html, template.key


def test_templates_command_lists_the_library() -> None:
    result = CliRunner().invoke(app, ["templates"])
    assert result.exit_code == 0
    for key in ENABLED_KEYS:
        assert f"[{key}]" in result.output
    assert "[G5]" in result.output
    assert "DISABLED" in result.output
