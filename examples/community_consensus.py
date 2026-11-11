"""Show how conformity q changes consensus in the S7 community scenario.

Run: uv run python examples/community_consensus.py --repeats 6
"""

from __future__ import annotations

import argparse
from pathlib import Path

from hnle.mc import run_monte_carlo
from hnle.spec import ModelSpec
from hnle.templates import load_template

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Conformity sensitivity for community discussion")
    parser.add_argument("--repeats", type=int, default=6)
    args = parser.parse_args()

    template = load_template(ROOT / "scenarios" / "s7_community_consensus.yaml")
    print(f"Scenario: {template.name_zh} / {template.name_en}")
    print(f"{'q':>5} {'diversity':>18} {'consensus step':>16} {'absorbing':>10}")
    for q in (1.0, 1.3, 1.8, 2.4):
        payload = template.spec.model_dump(mode="json")
        payload["q"] = q
        payload["repeats"] = args.repeats
        spec = ModelSpec.model_validate(payload)
        aggregate = run_monte_carlo(spec, template.graph, repeats=args.repeats)
        diversity = aggregate.metrics["diversity_final"]
        consensus = aggregate.metrics["time_to_consensus"]
        absorbing = aggregate.metrics["absorbing"]
        print(
            f"{q:>5.1f} {diversity.mean:>10.3f} [{diversity.ci95_lo:.2f}, "
            f"{diversity.ci95_hi:.2f}] {consensus.mean:>10.1f} {absorbing.mean:>10.2f}"
        )


if __name__ == "__main__":
    main()
