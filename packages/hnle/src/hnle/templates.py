"""Scenario template library.

Every template carries bilingual narrative metadata (question, data shape,
interpretation, assumptions, limitations) plus a validated ``ModelSpec`` and
graph definition. Election-style templates are gated behind a feature flag and
disabled by default.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from hnle.graph import Hypergraph
from hnle.io.scenario import load_scenario
from hnle.spec import ModelSpec

REQUIRED_TEXT_FIELDS = (
    "name",
    "question",
    "data_shape",
    "interpretation",
    "assumptions",
    "limitations",
)


@dataclass(frozen=True)
class Template:
    key: str
    name_zh: str
    name_en: str
    question_zh: str
    question_en: str
    data_shape_zh: str
    data_shape_en: str
    interpretation_zh: str
    interpretation_en: str
    assumptions_zh: str
    assumptions_en: str
    limitations_zh: str
    limitations_en: str
    spec: ModelSpec
    graph: Hypergraph
    path: Path
    feature_flag: str | None
    enabled_by_default: bool

    def is_enabled(self, environ: dict[str, str] | None = None) -> bool:
        if self.enabled_by_default:
            return True
        flag = (environ or dict(os.environ)).get((self.feature_flag or "").upper(), "")
        return flag.lower() in {"1", "true", "yes", "on"}


def _text(payload: dict[str, Any], base: str) -> tuple[str, str]:
    zh = str(payload.get(f"{base}_zh", "")).strip()
    en = str(payload.get(f"{base}_en", "")).strip()
    if not zh or not en:
        raise ValueError(f"template metadata missing {base}_zh/{base}_en")
    return zh, en


def load_template(path: str | Path) -> Template:
    template_path = Path(path)
    payload: Any = yaml.safe_load(template_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or "key" not in payload:
        raise ValueError(f"not a template file: {template_path}")
    texts = {base: _text(payload, base) for base in REQUIRED_TEXT_FIELDS}
    spec, graph, _ = load_scenario(template_path)
    return Template(
        key=str(payload["key"]),
        name_zh=texts["name"][0],
        name_en=texts["name"][1],
        question_zh=texts["question"][0],
        question_en=texts["question"][1],
        data_shape_zh=texts["data_shape"][0],
        data_shape_en=texts["data_shape"][1],
        interpretation_zh=texts["interpretation"][0],
        interpretation_en=texts["interpretation"][1],
        assumptions_zh=texts["assumptions"][0],
        assumptions_en=texts["assumptions"][1],
        limitations_zh=texts["limitations"][0],
        limitations_en=texts["limitations"][1],
        spec=spec,
        graph=graph,
        path=template_path,
        feature_flag=payload.get("feature_flag"),
        enabled_by_default=bool(payload.get("enabled_by_default", True)),
    )


def iter_templates(directory: str | Path = "scenarios") -> list[Template]:
    templates: list[Template] = []
    for path in sorted(Path(directory).glob("*.yaml")):
        try:
            templates.append(load_template(path))
        except ValueError:
            continue  # plain scenario files without template metadata
    return sorted(templates, key=lambda template: template.key)
