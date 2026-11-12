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
    assert 'lang="en"' in html
    assert "not a prediction of real opinion" in html
    assert "./sim.js" in html
    assert 'content="static"' in html
    assert "How to set these knobs" in html
    assert 'data-preset="quick"' in html
    assert 'id="scenarioBrief"' in html
    assert 'id="quality"' in html
    for lang in ("en", "zh", "ja", "de"):
        assert f'<option value="{lang}"' in html, lang
    assert ">English</option>" in html and ">Deutsch</option>" in html
    assert "data-tip-ja" in html and "data-tip-de" in html
    i18n = (ROOT / "apps" / "web" / "i18n.js").read_text(encoding="utf-8")
    assert "シナリオ・サンドボックス" in i18n
    assert "Szenario-Sandbox" in i18n


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
    # The checked-in site must be exactly the generated artifact: no drift
    # between apps/web and the Pages build.
    for name in ("index.html", "app.js", "templates.json"):
        assert (tmp_path / name).read_bytes() == (SITE / name).read_bytes(), name


def test_templates_export_matches_the_library(tmp_path: Path) -> None:
    payload = json.loads((SITE / "templates.json").read_text(encoding="utf-8"))
    assert len(payload) == 15
    keys = {item["key"] for item in payload}
    assert {"S2", "S7", "S9", "G1"} <= keys
    for item in payload:
        assert item["question_zh"] and item["question_en"]
        assert item["defaults"]["n_nodes"] > 0
        assert item["defaults"]["q"] > 0
        for field in ("decision", "real_world", "parameters", "watch"):
            assert item[f"{field}_zh"] and item[f"{field}_en"], (item["key"], field)
        assert item["defaults"]["steps"] > 0
        assert item["defaults"]["latency_dist"] in {"normal", "exponential", "lognormal", "const"}

    generated = tmp_path / "templates.json"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_static_templates.py"),
            "--output",
            str(generated),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(generated.read_text(encoding="utf-8")) == payload


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


def test_replay_and_3d_field_regressions() -> None:
    """Guards for the v1.4.0 replay/3D-deck fixes."""
    app = (ROOT / "apps" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("function play()")
    end = app.index("function downloadCsv()", start)
    play = app[start:end]
    assert "requestAnimationFrame(tick)" in play
    assert "setInterval" not in play
    assert "playback: true" in play
    assert "const playback = Boolean(options && options.playback)" in app
    assert "renderCharts(state.data, index, { playback: true })" in app

    field3d = (ROOT / "apps" / "web" / "field3d.js").read_text(encoding="utf-8")
    assert "if (reduce) this.draw" in field3d
    assert "global.__OPINIONLAB_PLAYBACK__ ? 12 : 30" in field3d
    assert "existing ? existing.height : 0.02" in field3d

    particles = (ROOT / "apps" / "web" / "particles.js").read_text(encoding="utf-8")
    assert "if (!this.particles.length) this.seed();" in particles
    assert "if (reduce) this.renderFrame();" in particles
