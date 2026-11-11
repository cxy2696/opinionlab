# Documentation

The documents below describe the model, the engine, the service and the
boundaries of the product. They are written for different readers, so the order
matters more than the length.

## Where to start

If you want to know what the product is for, read [Use cases](USE_CASES.md),
then [Demo](DEMO.md), then [Model card](MODEL_CARD.md).

If you want to understand the numbers, read [Math model](MATH_MODEL.md) and
[Conformance](CONFORMANCE.md). The first is the specification; the second maps
each equation to a function and a test. For a concrete input, read the
[case study](CASE_STUDY.md).

If you are deploying or operating the service, read
[Architecture](ARCHITECTURE.md), then [Runbook](RUNBOOK.md), then
[Compliance](COMPLIANCE.md) and [Capacity](capacity-report.md).

## All documents

| Document | Contents |
|---|---|
| [Use cases](USE_CASES.md) | six worked questions, commands and interpretation |
| [Demo](DEMO.md) | hosted and local demo, API, limits, Ollama narration |
| [Architecture](ARCHITECTURE.md) | layers, data flow, module map |
| [Math model](MATH_MODEL.md) | formulas, `q` limits, estimators and failure boundaries |
| [Case study](CASE_STUDY.md) | a published hashtag sample, from CSV to component result |
| [Conformance](CONFORMANCE.md) | equation-to-code map and the shared numerical fixture |
| [Model card](MODEL_CARD.md) | capabilities, limits, prohibited uses |
| [Compliance](COMPLIANCE.md) | regions, review, deletion, retention |
| [Runbook](RUNBOOK.md) | metrics, logs, rollback, tainted runs |
| [Capacity](capacity-report.md) | formula, calibration, load scenarios |
| [Changelog](../CHANGELOG.md) | behaviour changes and known deviations |

The repository documentation is English-only. The browser demo still offers an
optional Chinese interface translation for end users; that is a UI feature, not
a second set of documentation.
