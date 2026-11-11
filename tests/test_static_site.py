"""The GitHub Pages demo is assembled from shared frontend assets."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
SITE = ROOT / "site"


def test_static_site_sources_exist() -> None:
    for name in ("index.html", "app.js", "sim.js", "templates.json"):
        assert (SITE / name).exists(), name
    html = (SITE / "index.html").read_text(encoding="utf-8")
    assert "OpinionLab" in html
    assert "非对真实舆情的预测" in html
    assert "./sim.js" in html
    assert "这些参数到底在做什么" in html
    assert 'data-preset="quick"' in html


def test_build_script_assembles_shared_assets(tmp_path: Path) -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_site.py"), "--output", str(tmp_path)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    for name in ("index.html", "style.css", "app.js", "sim.js", "scene.js", "i18n.js",
                 "particles.js", "field3d.js", "galaxy.js", "templates.json", "echarts.min.js"):
        assert (tmp_path / name).exists(), name
    assert "3D" in (tmp_path / "index.html").read_text(encoding="utf-8")


def test_templates_export_matches_the_library() -> None:
    payload = json.loads((SITE / "templates.json").read_text(encoding="utf-8"))
    assert len(payload) == 15
    keys = {item["key"] for item in payload}
    assert {"S2", "S7", "S9", "G1"} <= keys
    for item in payload:
        assert item["question_zh"] and item["question_en"]
        assert item["defaults"]["n_nodes"] > 0
        assert item["defaults"]["q"] > 0


def test_browser_simulator_selftest() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    result = subprocess.run(
        [node, str(SITE / "sim.js"), "--selftest"],
        cwd=SITE,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout
