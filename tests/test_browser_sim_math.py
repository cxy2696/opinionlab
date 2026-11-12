"""The browser preview must use the same conformity map as the Python kernel."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from hnle.core.kernel import conformity_probabilities

ROOT = Path(__file__).parents[1]
SIM = ROOT / "site" / "sim.js"


def test_browser_conformity_matches_python_kernel() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    cases = [
        (5, 0, 1.5),
        (0, 5, 1.5),
        (3, 2, 1.0),
        (3, 2, 1.5),
        (2, 7, 2.2),
        (37, 100, 0.8),
    ]
    code = (
        f"const s=require({json.dumps(str(SIM))});"
        "console.log(JSON.stringify("
        + json.dumps(cases)
        + ".map(([ones,zeros,q])=>s.conformity(ones,zeros,q))));"
    )
    result = subprocess.run(
        [node, "-e", code], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout)
    for (ones, zeros, q), value in zip(cases, observed, strict=True):
        expected, _ = conformity_probabilities(
            np.asarray([[zeros, ones]], dtype=np.float64), q
        )
        assert value == pytest.approx(float(expected[0, 1]), rel=1e-12)
