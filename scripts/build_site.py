"""Assemble the GitHub Pages artifact from shared frontend sources.

The static site reuses the local demo's CSS and canvas modules; only
`index.html`, `app.js`, `sim.js` and `templates.json` are site-specific.
Run this before serving `site/` locally or uploading the Pages artifact.
"""

from __future__ import annotations

import argparse
import gzip
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED = ("style.css", "scene.js", "particles.js", "field3d.js", "galaxy.js", "i18n.js")


def build(output: Path) -> None:
    output = output.resolve()
    source = ROOT / "site"
    output.mkdir(parents=True, exist_ok=True)
    if output != source:
        for name in ("index.html", "app.js", "sim.js", "templates.json"):
            shutil.copy2(source / name, output / name)
    for name in SHARED:
        shutil.copy2(ROOT / "apps" / "web" / name, output / name)
    bundle = ROOT / "packages" / "hnle" / "src" / "hnle" / "assets" / "echarts.min.js.gz"
    (output / "echarts.min.js").write_bytes(gzip.decompress(bundle.read_bytes()))
    print(f"built static site assets in {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "site")
    build(parser.parse_args().output)
