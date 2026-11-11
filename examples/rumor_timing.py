"""Compare debunk timing on the S2 scenario.

Run: uv run python examples/rumor_timing.py --repeats 8
"""

from __future__ import annotations

import argparse
from pathlib import Path

from hnle.mc import run_monte_carlo
from hnle.spec import ModelSpec
from hnle.templates import load_template

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Debunk timing comparison")
    parser.add_argument("--repeats", type=int, default=8)
    parser.add_argument("--steps", type=int, default=80)
    args = parser.parse_args()

    template = load_template(ROOT / "scenarios" / "s2_rumor_debunk_timing.yaml")
    print(f"Scenario: {template.name_zh} / {template.name_en}")
    print(f"{'timing':>8} {'positive share':>16} {'95% CI':>24}")
    for at_step in (2, 12, 24):
        payload = template.spec.model_dump(mode="json")
        payload["n_steps"] = min(template.spec.n_steps, args.steps)
        payload["repeats"] = args.repeats
        interventions = list(payload.get("interventions") or [])
        interventions[0]["at_step"] = at_step
        payload["interventions"] = interventions
        spec = ModelSpec.model_validate(payload)
        aggregate = run_monte_carlo(spec, template.graph, repeats=args.repeats)
        share = aggregate.metrics["avg_share_final"]
        print(f"T+{at_step:<6} {share.mean:>16.3f} [{share.ci95_lo:.3f}, {share.ci95_hi:.3f}]")


if __name__ == "__main__":
    main()
