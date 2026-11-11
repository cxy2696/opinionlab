"""Single-file offline HTML report with mandatory disclaimer guardrails.

The report embeds the ECharts bundle inline (no CDN), uses a CSP nonce for its
inline script/style, forces the "simulation, not prediction" banner and refuses
to render when the disclaimer key is unknown or missing.
"""

from __future__ import annotations

import gzip
import html
import json
import secrets
from pathlib import Path
from typing import Any

import pandas as pd

from hnle.spec import ModelSpec

DISCLAIMERS: dict[str, tuple[str, str]] = {
    "simulation_not_prediction": (
        "本结果为基于给定假设的情景推演，非对真实舆情的预测。",
        "This result is a scenario simulation under stated assumptions, "
        "not a prediction of real public opinion.",
    )
}
DEFAULT_ASSUMPTIONS = (
    "结果依赖给定参数、拓扑与初始观点分布；外部事件未建模。",
    "Results depend on the given parameters, topology and initial opinions; "
    "exogenous events are not modelled.",
)
DEFAULT_LIMITATIONS = (
    "不用于个体预测；不包含平台算法、媒体议程与线下行为。",
    "Not for individual prediction; platform algorithms, media agenda and "
    "offline behaviour are not included.",
)
ASSET_DIR = Path(__file__).resolve().parent.parent / "assets"


class ReportError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


_BUNDLE: str | None = None


def echarts_bundle() -> str:
    global _BUNDLE
    if _BUNDLE is None:
        _BUNDLE = gzip.decompress((ASSET_DIR / "echarts.min.js.gz").read_bytes()).decode("utf-8")
    return _BUNDLE


def _table(rows: list[tuple[str, str]]) -> str:
    body = "\n".join(
        f"<tr><th>{html.escape(label)}</th><td>{html.escape(value)}</td></tr>"
        for label, value in rows
    )
    return f"<table>{body}</table>"


def _flatten(payload: dict[str, Any], prefix: str = "") -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for key, value in payload.items():
        name = f"{prefix}{key}"
        if isinstance(value, dict):
            rows.extend(_flatten(value, f"{name}."))
        else:
            rows.append((name, json.dumps(value, ensure_ascii=False)))
    return rows


def render_report(
    *,
    run_id: str,
    spec: ModelSpec,
    summary: dict[str, Any],
    frame: pd.DataFrame,
    manifest: dict[str, Any],
    aggregate: Any = None,
    disclaimer_key: str | None = "simulation_not_prediction",
    narrative: dict[str, str] | None = None,
    nonce: str | None = None,
    single_replica: bool | None = None,
    decision: dict[str, Any] | None = None,
) -> str:
    if not disclaimer_key or disclaimer_key not in DISCLAIMERS:
        raise ReportError(
            "DISCLAIMER_MISSING",
            f"disclaimer {disclaimer_key!r} is not registered; report generation aborted",
        )
    disclaimer_zh, disclaimer_en = DISCLAIMERS[disclaimer_key]
    token = nonce or secrets.token_hex(16)
    narrative = narrative or {}
    assumptions = (
        narrative.get("assumptions_zh", DEFAULT_ASSUMPTIONS[0]),
        narrative.get("assumptions_en", DEFAULT_ASSUMPTIONS[1]),
    )
    limitations = (
        narrative.get("limitations_zh", DEFAULT_LIMITATIONS[0]),
        narrative.get("limitations_en", DEFAULT_LIMITATIONS[1]),
    )
    if single_replica is None:
        single_replica = aggregate is None

    insufficient = aggregate is not None and aggregate.n < 30
    sample_badge = (
        '<span class="badge warn">样本不足 / insufficient samples '
        f'(n={aggregate.n})</span>'
        if insufficient
        else ""
    )
    watermark = (
        '<div class="watermark">单副本示意，非结论<br>Single replica — illustrative only</div>'
        if single_replica
        else ""
    )

    metric_rows = "".join(
        f"<tr><td>{html.escape(name)}</td><td>{html.escape(str(value))}</td></tr>"
        for name, value in summary.items()
    )

    ci_rows = ""
    ci_data: dict[str, dict[str, float]] = {}
    if aggregate is not None:
        for name, item in aggregate.metrics.items():
            ci_data[name] = {"mean": item.mean, "lo": item.ci95_lo, "hi": item.ci95_hi}
            ci_rows += (
                f"<tr><td>{html.escape(name)}</td><td>{item.mean:.6g}</td>"
                f"<td>{item.ci95_lo:.6g}</td><td>{item.ci95_hi:.6g}</td>"
                f"<td>{item.n}</td></tr>"
            )

    params = _table(_flatten(spec.model_dump(mode="json", by_alias=True)))

    decision_html = ""
    if decision:
        timing = decision.get("timing", {})
        def _cell(value: object) -> str:
            return "—" if value is None else str(value)

        rows = "".join(
            f"<tr><th>{label}</th><td>{_cell(timing.get(key))}</td></tr>"
            for key, label in (
                ("takeoff_step", "级联起势 / Cascade take-off"),
                ("peak_step", "级联峰值 / Cascade peak"),
                ("consensus_step", "达到多数 / Majority"),
                ("intervention_step", "本次干预 / Intervention"),
            )
        )
        followups = "".join(
            f"<li>{html.escape(zh)}<br><span class='en'>{html.escape(en)}</span></li>"
            for zh, en in zip(
                decision.get("followups_zh", []), decision.get("followups_en", []), strict=False
            )
        )
        decision_html = f"""
<h2>决策提示 / Decision brief</h2>
<p><strong>这项推演帮助判断 / What it informs:</strong>
 {html.escape(decision.get("decision_zh", ""))} / {html.escape(decision.get("decision_en", ""))}</p>
<table>{rows}</table>
<p><strong>时机窗口 / Window:</strong> {html.escape(decision.get("window_zh", ""))}<br>
<span class="en">{html.escape(decision.get("window_en", ""))}</span></p>
<h3>建议后续 / Next steps</h3>
<ul>{followups}</ul>
<p class="note">{html.escape(decision.get("caveat_zh", ""))}<br>
{html.escape(decision.get("caveat_en", ""))}</p>
"""

    manifest_json = html.escape(json.dumps(manifest, ensure_ascii=False, indent=2))
    series = {
        "steps": frame["step"].tolist(),
        "diversity": frame["diversity"].tolist(),
    }
    metrics_chart = {
        name: ci_data[name]
        for name in ("diversity_final", "cascade_p99", "time_to_consensus", "absorbing")
        if name in ci_data
    }
    chart_watermark = (
        "单副本示意，非结论 / illustrate only" if single_replica else ""
    )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy"
      content="default-src 'none'; style-src 'nonce-{token}'; script-src 'nonce-{token}'">
<title>OpinionLab · {html.escape(run_id)}</title>
<style nonce="{token}">
body {{ font-family: -apple-system, "Segoe UI", sans-serif; margin: 2rem; color: #1f2933; }}
.banner {{ background: #fff4e5; border-left: 4px solid #f0a020;
           padding: .8rem 1rem; margin-bottom: 1.5rem; }}
.badge {{ display: inline-block; padding: .1rem .5rem; border-radius: 6px;
          font-size: .8rem; margin-left: .5rem; }}
.badge.warn {{ background: #fde2e1; color: #9b1c1c; }}
table {{ border-collapse: collapse; width: 100%; max-width: 900px; margin-bottom: 1rem; }}
td, th {{ border-bottom: 1px solid #e4e7eb; padding: .35rem .6rem; text-align: left; }}
code {{ background: #f5f7fa; padding: .1rem .3rem; }}
.chart {{ width: 100%; max-width: 900px; height: 320px; }}
details pre {{ background: #f5f7fa; padding: .8rem; overflow-x: auto; max-height: 320px; }}
.en {{ color: #627d98; font-size: .9em; }}
.note {{ background: #f5f7fa; padding: .6rem .8rem; font-size: .85rem; color: #486581; }}
.watermark {{ position: fixed; inset: 0; display: flex; align-items: center;
  justify-content: center; pointer-events: none; font-size: 3rem; color: rgba(200,0,0,.12);
  transform: rotate(-25deg); font-weight: 700; text-align: center; }}
</style>
</head>
<body>
<h1>OpinionLab 仿真报告 / Simulation report</h1>
<div class="banner"><strong>免责声明 / Disclaimer:</strong> {disclaimer_zh}<br>{disclaimer_en}</div>
{sample_badge}
<p>run_id: <code>{html.escape(run_id)}</code> · engine: {spec.engine} · q={spec.q}
 · seed={spec.seed} · repeats={spec.repeats}</p>
{decision_html}
<h2>多样性曲线 / Diversity series</h2>
<div id="diversityChart" class="chart"></div>
<h2>蒙特卡洛 95% CI / Monte-Carlo CI</h2>
<table><thead><tr><th>metric</th><th>mean</th><th>ci95_lo</th><th>ci95_hi</th><th>n</th></tr></thead>
<tbody>{ci_rows or '<tr><td colspan="5">单副本 / single replica</td></tr>'}</tbody></table>
<div id="metricChart" class="chart"></div>
<h2>指标 / Metrics</h2>
<table><tbody>{metric_rows}</tbody></table>
<h2>参数 / Parameters</h2>
{params}
<h2>假设 / Assumptions</h2>
<p>{html.escape(assumptions[0])}<br>{html.escape(assumptions[1])}</p>
<h2>局限 / Limitations</h2>
<p>{html.escape(limitations[0])}<br>{html.escape(limitations[1])}</p>
<h2>生成方式 / Generation</h2>
<p>本报告由确定性仿真引擎生成，不含生成式内容；如未来引入生成式段落，将显式标识并需人工复核。<br>
This report is produced by a deterministic simulation engine and contains no
generative content; any future generated section will be labelled and reviewed.</p>
<details><summary>manifest / 运行清单</summary><pre>{manifest_json}</pre></details>
{watermark}
<script nonce="{token}">{echarts_bundle()}</script>
<script nonce="{token}">
(function () {{
  var series = {json.dumps(series)};
  var metrics = {json.dumps(metrics_chart)};
  var wm = {json.dumps(chart_watermark)};
  var d = document.getElementById('diversityChart');
  var chart = echarts.init(d);
  chart.setOption({{
    tooltip: {{ trigger: 'axis' }},
    xAxis: {{ type: 'category', data: series.steps }},
    yAxis: {{ type: 'value', min: 0, max: 0.5 }},
    series: [{{ type: 'line', data: series.diversity, smooth: true }}],
    graphic: wm ? [{{ type: 'text', left: 'center', top: 'middle',
      style: {{ text: wm, fontSize: 26, fill: 'rgba(200,0,0,0.15)' }} }}] : []
  }});
  var m = document.getElementById('metricChart');
  var chart2 = echarts.init(m);
  var names = Object.keys(metrics);
  chart2.setOption({{
    tooltip: {{}},
    grid: {{ left: 140 }},
    xAxis: {{ type: 'value' }},
    yAxis: {{ type: 'category', data: names }},
    series: [
      {{ type: 'bar', stack: 'ci', data: names.map(function (n) {{ return metrics[n].lo; }}),
         itemStyle: {{ color: 'transparent' }} }},
      {{ type: 'bar', stack: 'ci',
         data: names.map(function (n) {{ return metrics[n].hi - metrics[n].lo; }}),
         itemStyle: {{ color: '#cbd5e0' }} }},
      {{ type: 'scatter', data: names.map(function (n) {{
           return [metrics[n].mean, n]; }}) }}
    ]
  }});
  window.addEventListener('resize', function () {{ chart.resize(); chart2.resize(); }});
}})();
</script>
<p><small>Generated by hnle · offline single file · no external requests.</small></p>
</body>
</html>
"""
