"""Export enabled scenario templates for the static GitHub Pages demo."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from hnle.templates import iter_templates

ROOT = Path(__file__).resolve().parents[1]


def export_templates(output: Path | None = None) -> list[dict[str, object]]:
    """Return the enabled templates in the shape consumed by the web client."""
    payload: list[dict[str, object]] = []
    for template in iter_templates(ROOT / "scenarios"):
        if not template.is_enabled():
            continue
        intervention = None
        if template.spec.interventions:
            item = template.spec.interventions[0]
            intervention = {
                "at_step": item.at_step,
                "type": item.type.value,
                "magnitude": item.magnitude,
                "duration": item.duration,
                "target": item.target,
            }
        payload.append(
            {
                "key": template.key,
                "name_zh": template.name_zh,
                "name_en": template.name_en,
                "question_zh": template.question_zh,
                "question_en": template.question_en,
                "data_shape_zh": template.data_shape_zh,
                "data_shape_en": template.data_shape_en,
                "interpretation_zh": template.interpretation_zh,
                "interpretation_en": template.interpretation_en,
                "assumptions_zh": template.assumptions_zh,
                "assumptions_en": template.assumptions_en,
                "limitations_zh": template.limitations_zh,
                "limitations_en": template.limitations_en,
                "decision_zh": template.decision_zh,
                "decision_en": template.decision_en,
                "real_world_zh": template.real_world_zh,
                "real_world_en": template.real_world_en,
                "parameters_zh": template.parameters_zh,
                "parameters_en": template.parameters_en,
                "watch_zh": template.watch_zh,
                "watch_en": template.watch_en,
                "defaults": {
                    "q": template.spec.q,
                    "latency_mu": template.spec.latency.mu,
                    "latency_sigma": template.spec.latency.sigma,
                    "latency_dist": template.spec.latency.dist.value,
                    "steps": min(template.spec.n_steps, 200),
                    "n_steps": min(template.spec.n_steps, 200),
                    "repeats": max(template.spec.repeats, 8),
                    "seed": template.spec.seed,
                    "n_nodes": template.graph.n_nodes,
                    "n_edges": len(template.graph.hyperedges),
                    "min_size": template.spec.hyperedge.min_size,
                    "max_size": template.spec.hyperedge.max_size,
                    "init_mode": template.spec.init_mode.value,
                    "target_share_1": template.spec.target_share_1,
                },
                "intervention": intervention,
            }
        )
    target = output or ROOT / "site" / "templates.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(payload)} templates to {target}")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "site" / "templates.json")
    export_templates(parser.parse_args().output)


if __name__ == "__main__":
    main()
