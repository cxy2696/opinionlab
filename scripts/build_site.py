"""Assemble the GitHub Pages artifact from the shared web client.

Single source of truth:
  - `apps/web/index.html` is the page shell for both surfaces. The static build
    only rewrites asset URLs and flips the mode meta tag.
  - `apps/web/app.js` is the one client for both surfaces.
  - `site/sim.js` is the only site-specific script (the browser simulator).
  - `site/templates.json` is generated from the scenario library.

Run this before serving `site/` locally or uploading the Pages artifact.
"""

from __future__ import annotations

import argparse
import gzip
import shutil
from pathlib import Path

from build_static_templates import export_templates

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "web"
SITE = ROOT / "site"
SHARED = ("style.css", "scene.js", "particles.js", "field3d.js", "galaxy.js", "i18n.js", "app.js")
SITE_ONLY = ("sim.js",)


def render_index() -> str:
    """Return the static page shell derived from the local-service shell."""
    html = (WEB / "index.html").read_text(encoding="utf-8")
    html = html.replace("/api/v1/demo/static/", "./")
    html = html.replace("/api/v1/demo/echarts.js", "./echarts.min.js")
    html = html.replace(
        '<meta name="opinionlab-mode" content="api">',
        '<meta name="opinionlab-mode" content="static">',
    )
    html = html.replace("<!-- static-sim -->", '<script defer src="./sim.js"></script>')
    return html


def build(output: Path) -> None:
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    (output / "index.html").write_text(render_index(), encoding="utf-8")
    for name in SHARED:
        source = WEB / name
        if source.resolve() != (output / name).resolve():
            shutil.copy2(source, output / name)
    for name in SITE_ONLY:
        source = SITE / name
        if source.resolve() != (output / name).resolve():
            shutil.copy2(source, output / name)
    export_templates(output / "templates.json")
    bundle = ROOT / "packages" / "hnle" / "src" / "hnle" / "assets" / "echarts.min.js.gz"
    (output / "echarts.min.js").write_bytes(gzip.decompress(bundle.read_bytes()))
    print(f"built static site assets in {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "site")
    build(parser.parse_args().output)
