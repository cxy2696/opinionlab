# OpinionLab · Scenario Sandbox

[![CI](https://github.com/cxy2696/opinionlab/actions/workflows/ci.yml/badge.svg)](https://github.com/cxy2696/opinionlab/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**中文** · [English](README_en.md) · [完整中文说明](README_cn.md)

**把“一群人会怎么想”变成可重复的实验。**
A sandbox for how opinions spread through groups — reproducible, with uncertainty ranges.

![OpinionLab demo](docs/demo.png)

**在线体验 / Live demo:** https://cxy2696.github.io/opinionlab/

---

## 选择语言 / Choose a language

| 中文 | English |
|---|---|
| [中文完整说明](README_cn.md) | [Full English README](README_en.md) |
| [使用场景](docs/USE_CASES_cn.md) | [Use cases](docs/USE_CASES_en.md) |
| [产品演示](docs/DEMO_cn.md) | [Demo](docs/DEMO_en.md) |
| [架构](docs/ARCHITECTURE_cn.md) | [Architecture](docs/ARCHITECTURE_en.md) |
| [数学模型](docs/MATH_MODEL_cn.md) | [Math model](docs/MATH_MODEL_en.md) |
| [模型卡](docs/MODEL_CARD_cn.md) | [Model card](docs/MODEL_CARD_en.md) |
| [合规](docs/COMPLIANCE_cn.md) | [Compliance](docs/COMPLIANCE_en.md) |
| [运维手册](docs/RUNBOOK_cn.md) | [Runbook](docs/RUNBOOK_en.md) |
| [容量报告](docs/capacity-report_cn.md) | [Capacity](docs/capacity-report_en.md) |
| [变更日志](CHANGELOG_cn.md) | [Changelog](CHANGELOG_en.md) |

## 30 秒上手 / 30-second start

```bash
git clone https://github.com/cxy2696/opinionlab.git
cd opinionlab
make demo        # http://127.0.0.1:8000
```

或直接打开在线版，无需安装：https://cxy2696.github.io/opinionlab/

- 15 个中英双语场景模板 / 15 bilingual templates
- 3D 工业风追踪视图，中英一键切换 / 3D industrial tracker with EN/中文 switch
- 每个参数都有“是什么 / 为什么调”的解释 / every parameter explained in plain language
- 决策提示、关键时点与后续验证 / decision brief, timing nodes and next checks

## License

MIT
