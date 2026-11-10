"""disclaimer enforcement, offline bundle, watermark and sample badges."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from hnle.core.sparse import run_sparse
from hnle.graph import random_hypergraph
from hnle.io.export import export_run
from hnle.io.report import ReportError, render_report
from hnle.mc import run_monte_carlo
from hnle.spec import ModelSpec


def _case() -> tuple[ModelSpec, object]:
    spec = ModelSpec(n_steps=20, seed=4, repeats=3, latency={"dist": "const", "mu": 1})
    graph = random_hypergraph(40, 80, np.random.default_rng(4), spec.hyperedge)
    return spec, graph


def _export(tmp_path: Path, *, aggregate: object = None, **kwargs: object) -> Path:
    spec, graph = _case()
    result = run_sparse(spec, graph, spec.seed)
    paths = export_run(spec, graph, result, tmp_path, aggregate=aggregate, **kwargs)
    return paths["report"]


def test_report_is_single_file_with_inline_echarts(tmp_path: Path) -> None:
    spec, graph = _case()
    aggregate = run_monte_carlo(spec, graph, repeats=3)
    report = _export(tmp_path, aggregate=aggregate, nonce="fixednonce")
    html = report.read_text(encoding="utf-8")
    assert "echarts" in html.lower()
    assert "nonce-fixednonce" in html
    assert 'src="http' not in html
    assert "单副本示意" not in html  # MC report, no single-replica watermark
    assert "<details>" in html
    assert "假设 / Assumptions" in html
    assert "局限 / Limitations" in html
    assert "95% CI" in html


def test_insufficient_samples_badge(tmp_path: Path) -> None:
    spec, graph = _case()
    aggregate = run_monte_carlo(spec, graph, repeats=3)
    report = _export(tmp_path, aggregate=aggregate)
    html = report.read_text(encoding="utf-8")
    assert "样本不足" in html
    assert "insufficient samples" in html


def test_single_replica_report_has_watermark(tmp_path: Path) -> None:
    report = _export(tmp_path)
    html = report.read_text(encoding="utf-8")
    assert "单副本示意，非结论" in html
    assert "illustrative only" in html
    assert "95% CI" in html  # section still renders, marked single replica


def test_missing_disclaimer_aborts_generation() -> None:
    from hnle.io.export import series_frame

    spec, graph = _case()
    result = run_sparse(spec, graph, spec.seed)
    with pytest.raises(ReportError) as exc:
        render_report(
            run_id="x",
            spec=spec,
            summary={"diversity_final": result.diversity_series[-1]},
            frame=series_frame(result),
            manifest={},
            disclaimer_key="not_registered",
        )
    assert exc.value.code == "DISCLAIMER_MISSING"
