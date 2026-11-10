"""ModelSpec is the single source of truth and validates everywhere."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from hnle.spec import (
    Aggregation,
    DecisionRule,
    Engine,
    InitMode,
    InterventionType,
    LatencyDist,
    MetricName,
    ModelSpec,
    ShockType,
    load_spec,
    save_spec,
)


def test_defaults_match_spec() -> None:
    spec = ModelSpec()
    assert spec.engine is Engine.sparse_vector
    assert spec.n_steps == 1000
    assert spec.seed == 42
    assert spec.repeats == 50
    assert spec.q == 1.5
    assert spec.decision_rule is DecisionRule.stochastic
    assert spec.init_mode is InitMode.data_driven
    assert spec.n_opinions == 2
    assert spec.aggregation is Aggregation.mean
    assert spec.latency.dist is LatencyDist.normal
    assert spec.latency.mu == 5.0
    assert spec.latency.sigma == 2.0
    assert spec.hyperedge.min_size == 2
    assert spec.hyperedge.max_size == 200
    assert spec.consensus_threshold == 0.8
    assert spec.absorb_check is True
    assert spec.metrics == list(MetricName)


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"q": 0}, "q"),
        ({"q": 21}, "q"),
        ({"n_opinions": 1}, "n_opinions"),
        ({"n_opinions": 7}, "n_opinions"),
        ({"repeats": 0}, "repeats"),
        ({"consensus_threshold": 0.4}, "consensus_threshold"),
        ({"n_steps": 0}, "n_steps"),
        ({"seed": -1}, "seed"),
        ({"init_mode": "fixed_ratio", "target_share_1": 1.5}, "target_share_1"),
        ({"threshold": 1.2}, "threshold"),
        ({"hyperedge": {"min_size": 10, "max_size": 5}}, "hyperedge"),
        ({"weights": {"source": "custom"}}, "weights"),
        ({"latency": {"dist": "exponential", "mu": -1}}, "mu"),
    ],
)
def test_invalid_values_name_the_field(payload: dict[str, object], field: str) -> None:
    with pytest.raises(ValidationError) as exc:
        ModelSpec.model_validate(payload)
    locations = [".".join(str(part) for part in err["loc"]) for err in exc.value.errors()]
    assert any(field in loc for loc in locations), locations


def test_exponential_lambda_derived_from_mu() -> None:
    spec = ModelSpec.model_validate({"latency": {"dist": "exponential", "mu": 4}})
    assert spec.latency.lam == pytest.approx(0.25)


def test_explicit_lambda_is_kept_and_serialised_by_alias() -> None:
    spec = ModelSpec.model_validate({"latency": {"dist": "exponential", "lambda": 0.2}})
    assert spec.latency.lam == pytest.approx(0.2)
    dumped = spec.model_dump(mode="json", by_alias=True)
    assert dumped["latency"]["lambda"] == pytest.approx(0.2)
    assert "lam" not in dumped["latency"]


def test_unknown_fields_rejected() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ModelSpec.model_validate({"q": 1.0, "n_steps_typo": 10})


def test_metrics_subset_and_unknown_rejected() -> None:
    spec = ModelSpec.model_validate({"metrics": ["diversity_final", "cascade_p99"]})
    assert spec.metrics == [MetricName.diversity_final, MetricName.cascade_p99]
    with pytest.raises(ValidationError):
        ModelSpec.model_validate({"metrics": ["not_a_metric"]})


def test_shocks_and_interventions_validate() -> None:
    spec = ModelSpec.model_validate(
        {
            "shocks": [{"at_step": 5, "type": "flip_share", "magnitude": 0.3}],
            "interventions": [
                {
                    "at_step": 20,
                    "type": "debunk",
                    "target": {"hashtag": "policy-a"},
                    "magnitude": 0.3,
                    "duration": 10,
                }
            ],
        }
    )
    assert spec.shocks[0].type is ShockType.flip_share
    assert spec.interventions[0].type is InterventionType.debunk
    with pytest.raises(ValidationError):
        ModelSpec.model_validate({"interventions": [{"at_step": 1, "type": "debunk",
                                                      "magnitude": 2.0, "duration": 1}]})


def test_json_roundtrip_and_dump_is_rewritable() -> None:
    spec = ModelSpec.model_validate({"q": 2.0, "n_opinions": 3, "metrics": ["entropy_final"]})
    dumped = spec.model_dump(mode="json")
    assert ModelSpec.model_validate(dumped) == spec
    assert ModelSpec.model_validate_json(spec.canonical_json()) == spec


def test_canonical_json_is_stable_and_hashable() -> None:
    a = ModelSpec.model_validate({"q": 2.0, "latency": {"dist": "const", "mu": 3}})
    b = ModelSpec.model_validate({"latency": {"mu": 3, "dist": "const"}, "q": 2.0})
    assert a.canonical_json() == b.canonical_json()
    digest = a.config_sha256()
    assert re.fullmatch(r"[0-9a-f]{64}", digest)
    assert digest == b.config_sha256()
    assert a.config_sha256() != ModelSpec(q=2.5, latency={"dist": "const", "mu": 3}).config_sha256()


def test_load_and_save_yaml_and_json(tmp_path: Path) -> None:
    yaml_path = tmp_path / "scenario.yaml"
    yaml_path.write_text(
        "q: 2.0\nn_opinions: 3\nlatency:\n  dist: exponential\n  mu: 4\n", encoding="utf-8"
    )
    spec = load_spec(yaml_path)
    assert spec.q == 2.0
    assert spec.latency.lam == pytest.approx(0.25)

    json_path = tmp_path / "scenario.json"
    save_spec(spec, json_path)
    assert load_spec(json_path) == spec

    yaml_out = tmp_path / "copy.yaml"
    save_spec(spec, yaml_out)
    assert load_spec(yaml_out) == spec


def test_bad_spec_file_reports_field_path(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text("q: 0\n", encoding="utf-8")
    with pytest.raises(ValidationError) as exc:
        load_spec(path)
    assert exc.value.errors()[0]["loc"] == ("q",)

    bad_top = tmp_path / "list.json"
    bad_top.write_text(json.dumps([1, 2]), encoding="utf-8")
    with pytest.raises(ValueError, match="mapping"):
        load_spec(bad_top)


def test_all_enum_values_are_lower_snake_case() -> None:
    for enum_cls in (
        Engine,
        DecisionRule,
        InitMode,
        LatencyDist,
        Aggregation,
        ShockType,
        InterventionType,
    ):
        for member in enum_cls:
            assert re.fullmatch(r"[a-z][a-z0-9_]*", member.value), member
            assert member.value == member.value.lower()
