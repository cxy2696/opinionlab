"""documentation, golden freeze, changelog and launch checklist."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_architecture_and_math_docs() -> None:
    architecture = (ROOT / "docs" / "ARCHITECTURE.md").read_text(encoding="utf-8")
    math_model = (ROOT / "docs" / "MATH_MODEL.md").read_text(encoding="utf-8")
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
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    for marker in ("OPT-01", "SeedSequence", "decision_rule", "manifest", "Known deviations"):
        assert marker in changelog


def test_readme_points_at_docs() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for doc in ("ARCHITECTURE.md", "MATH_MODEL.md", "MODEL_CARD.md", "COMPLIANCE.md",
                "RUNBOOK.md", "capacity-report.md", "DEMO.md", "USE_CASES.md",
                "CHANGELOG.md"):
        assert doc in readme
