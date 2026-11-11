# OpinionLab · Scenario Sandbox

[![CI](https://github.com/cxy2696/opinionlab/actions/workflows/ci.yml/badge.svg)](https://github.com/cxy2696/opinionlab/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](pyproject.toml)

**English** · [中文](README_cn.md) · [Full English guide](README_en.md)

**Turn “how would this group react?” into an experiment you can repeat.**
A sandbox for how opinions spread through groups — reproducible, with uncertainty ranges.

![OpinionLab demo](docs/demo.png)

**Live demo:** https://cxy2696.github.io/opinionlab/

---

## What it is

OpinionLab simulates group opinion with hypergraphs, non-linear conformity `q` and heterogeneous
latency. It returns scenario ranges with 95% confidence intervals and a plain-language decision
brief — not a single-point forecast.

模型用超图、非线性从众 `q` 与异质时延模拟群体观点，输出带 95% 置信区间的情景范围与“能支持什么判断”的说明，
而不是单点预测。详见 [中文说明](README_cn.md)。

## Highlights

- **15 bilingual templates:** crisis communication, community, organizational change, product launch,
  policy, research.
- **3D industrial cockpit:** galaxy backdrop, rotating opinion network, target lock and telemetry.
- **3D telemetry array:** opinion terrain, cascade bars and stance cloud with readouts, legends and
  hover values.
- **Explained parameters:** every knob has “what / why”, hover tips and presets.
- **Decision brief:** timing nodes, a simulated action window and follow-up checks.
- **Optional local Ollama:** assistive narration, off by default, never used for metrics or conclusions.

## 30-second start

```bash
git clone https://github.com/cxy2696/opinionlab.git
cd opinionlab
make demo        # http://127.0.0.1:8000
```

Or open the hosted demo: https://cxy2696.github.io/opinionlab/

```bash
make check       # ruff + mypy --strict + pytest
uv run python examples/rumor_timing.py --repeats 8
```

## Documentation

| English | 中文 |
|---|---|
| [Full English guide](README_en.md) | [完整中文说明](README_cn.md) |
| [Docs index](docs/README_en.md) | [文档导航](docs/README_cn.md) |
| [Use cases](docs/USE_CASES_en.md) | [使用场景](docs/USE_CASES_cn.md) |
| [Demo](docs/DEMO_en.md) | [产品演示](docs/DEMO_cn.md) |
| [Architecture](docs/ARCHITECTURE_en.md) | [架构](docs/ARCHITECTURE_cn.md) |
| [Math model](docs/MATH_MODEL_en.md) | [数学模型](docs/MATH_MODEL_cn.md) |
| [Model card](docs/MODEL_CARD_en.md) | [模型卡](docs/MODEL_CARD_cn.md) |
| [Compliance](docs/COMPLIANCE_en.md) | [合规](docs/COMPLIANCE_cn.md) |
| [Runbook](docs/RUNBOOK_en.md) | [运维手册](docs/RUNBOOK_cn.md) |
| [Capacity](docs/capacity-report_en.md) | [容量报告](docs/capacity-report_cn.md) |
| [Changelog](CHANGELOG_en.md) | [变更日志](CHANGELOG_cn.md) |

## Repository at a glance

| Path | What it is |
|---|---|
| `packages/hnle/` | Standalone simulation engine: model, kernels, metrics, Monte Carlo, reports |
| `apps/api/` | FastAPI service: auth, quotas, jobs, compliance, demo API |
| `apps/web/` | Local demo frontend source; `site/` reuses it at build time |
| `scenarios/` | 15 bilingual templates |
| `tests/` | Unit, integration, golden, frontend and documentation tests |
| `docs/` | Paired English/Chinese math, architecture, compliance and operations docs |

## License

MIT
