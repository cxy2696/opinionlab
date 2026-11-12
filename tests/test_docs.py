"""documentation policy, golden freeze and changelog checks."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).parents[1]
CJK = re.compile(r"[\u4e00-\u9fff]")


def test_architecture_and_math_docs() -> None:
    architecture = (ROOT / "docs" / "ARCHITECTURE.md").read_text(encoding="utf-8")
    math_model = (ROOT / "docs" / "MATH_MODEL.md").read_text(encoding="utf-8")
    assert "hnle" in architecture and "FastAPI" in architecture
    assert "S_x(e)" in math_model or "S_x" in math_model
    assert "aggregate_node_probabilities" in math_model
    assert "conformity_probabilities" in math_model
    assert "argmax" in math_model and "stochastic" in math_model
    assert "threshold" in math_model


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
    for base in ("ARCHITECTURE", "MATH_MODEL", "CONFORMANCE", "CASE_STUDY", "MODEL_CARD",
                 "COMPLIANCE", "RUNBOOK", "capacity-report", "DEMO", "USE_CASES"):
        assert f"docs/{base}.md" in readme
        assert (ROOT / "docs" / f"{base}.md").exists()
    assert "CHANGELOG.md" in readme


def _markdown_files() -> list[Path]:
    return [
        path
        for path in ROOT.rglob("*.md")
        if not any(
            part in {".git", ".venv", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
            for part in path.parts
        )
    ]


def test_relative_doc_links_and_images_resolve() -> None:
    pattern = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
    issues: list[str] = []
    for path in _markdown_files():
        text = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.S)
        for target in pattern.findall(text):
            target = target.strip().strip("<>")
            if target.startswith(("http://", "https://", "mailto:", "tel:", "#")):
                continue
            relative = unquote(target.split("#", 1)[0])
            if not relative:
                continue
            destination = (path.parent / relative).resolve()
            if not destination.exists():
                issues.append(f"{path.relative_to(ROOT)} -> {target}")
    assert not issues, "missing relative docs targets:\n" + "\n".join(issues)


def test_visible_version_matches_package_version() -> None:
    version = re.search(
        r'^version = "([^"]+)"', (ROOT / "pyproject.toml").read_text(encoding="utf-8"), re.M
    )
    assert version is not None
    expected = version.group(1)
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert f"[![Version: {expected}]" in readme
    docs_index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    assert f"**Applies to:** OpinionLab v{expected}" in docs_index
    for name in ("apps/web/index.html", "site/index.html"):
        html = (ROOT / name).read_text(encoding="utf-8")
        assert f"BUILD <b>V{expected}</b>" in html, name
    api = (ROOT / "apps" / "api" / "app" / "main.py").read_text(encoding="utf-8")
    assert f'version="{expected}"' in api
    for name in ("deploy/k8s/helm-cn/values.yaml", "deploy/k8s/helm-global/values.yaml"):
        values = (ROOT / name).read_text(encoding="utf-8")
        assert f'tag: "{expected}"' in values, name
    for path in _markdown_files():
        assert expected in path.read_text(encoding="utf-8"), path.relative_to(ROOT)


def test_documentation_is_english_only() -> None:
    for path in _markdown_files():
        assert not path.name.endswith(("_cn.md", "_en.md")), f"language-tagged doc: {path}"
        text = path.read_text(encoding="utf-8")
        assert not CJK.search(text), f"non-English text in {path}"
