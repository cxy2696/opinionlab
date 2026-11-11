"""The documented examples run end-to-end."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]


def _run(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "examples" / script), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_rumor_timing_example() -> None:
    result = _run("rumor_timing.py", "--repeats", "2", "--steps", "20")
    assert result.returncode == 0, result.stderr
    assert "T+2" in result.stdout
    assert "T+12" in result.stdout
    assert "95% CI" in result.stdout


def test_community_consensus_example() -> None:
    result = _run("community_consensus.py", "--repeats", "2")
    assert result.returncode == 0, result.stderr
    assert "diversity" in result.stdout
    assert "1.0" in result.stdout
