"""documentation, golden freeze, changelog and launch checklist."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_architecture_and_math_docs() -> None:
    architecture = (ROOT / "docs" / "ARCHITECTURE_cn.md").read_text(encoding="utf-8")
    math_model = (ROOT / "docs" / "MATH_MODEL_cn.md").read_text(encoding="utf-8")
    assert "hnle" in architecture and "FastAPI" in architecture
    assert "S_x(e)" in math_model or "S_x" in math_model
    assert "aggregate_node_probabilities" in math_model
    assert "argmax" in math_model and "stochastic" in math_model
    assert "公式 (3)" in math_model or "公式(3)" in math_model


def test_five_golden_configurations_are_frozen() -> None:
    baseline = json.loads((ROOT / "tests" / "golden" / "v1_baseline.json").read_text())
    assert len(baseline) == 5
    for metrics in baseline.values():
        for key in ("diversity_final", "cascade_p99", "time_to_consensus"):
            assert key in metrics


def test_changelog_records_behaviour_changes() -> None:
    changelog = (ROOT / "CHANGELOG_cn.md").read_text(encoding="utf-8")
    for marker in ("OPT-01", "SeedSequence", "decision_rule", "manifest", "Known deviations"):
        assert marker in changelog


def test_readme_points_at_docs() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for base in ("ARCHITECTURE", "MATH_MODEL", "MODEL_CARD", "COMPLIANCE",
                 "RUNBOOK", "capacity-report", "DEMO", "USE_CASES"):
        assert f"docs/{base}_cn.md" in readme or f"docs/{base}_en.md" in readme
        assert (ROOT / "docs" / f"{base}_cn.md").exists()
        assert (ROOT / "docs" / f"{base}_en.md").exists()
    assert "CHANGELOG_cn.md" in readme and "CHANGELOG_en.md" in readme


def test_every_markdown_has_chinese_and_english_editions() -> None:
    for path in ROOT.rglob("*.md"):
        if any(part in {".git", ".venv", ".pytest_cache", ".mypy_cache"} for part in path.parts):
            continue
        if path.name == "README.md":
            continue
        assert path.name.endswith(("_cn.md", "_en.md")), f"unpaired doc: {path}"
        counterpart = path.with_name(path.name[:-6] + ("_en.md" if path.name.endswith("_cn.md") else "_cn.md"))
        assert counterpart.exists(), f"missing {counterpart}"
