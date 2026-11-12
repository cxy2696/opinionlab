"""ModelSpec — the single source of truth for every simulation parameter.

CLI, API and engine all validate against this object, so parameter names and
constraints cannot drift between layers. Loaded from YAML or JSON, dumped back
with ``model_dump(mode="json")``, and hashed canonically for run manifests.
"""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from pathlib import Path
from typing import Any, Self

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Engine(StrEnum):
    sparse_vector = "sparse_vector"
    event_driven = "event_driven"


class DecisionRule(StrEnum):
    stochastic = "stochastic"
    argmax = "argmax"
    threshold = "threshold"


class InitMode(StrEnum):
    data_driven = "data_driven"
    balanced_random = "balanced_random"
    fixed_ratio = "fixed_ratio"


class LatencyDist(StrEnum):
    normal = "normal"
    exponential = "exponential"
    lognormal = "lognormal"
    const = "const"


class LatencyQuantize(StrEnum):
    integer_steps = "integer_steps"
    continuous = "continuous"


class WeightSource(StrEnum):
    uniform = "uniform"
    engagement = "engagement"
    centrality = "centrality"
    custom = "custom"


class WeightNormalize(StrEnum):
    max = "max"
    none = "none"


class Aggregation(StrEnum):
    mean = "mean"
    max = "max"
    size_weighted = "size_weighted"


class TopologyMode(StrEnum):
    static = "static"
    time_varying = "time_varying"


class ShockType(StrEnum):
    flip_share = "flip_share"
    edge_boost = "edge_boost"
    new_opinion = "new_opinion"


class InterventionType(StrEnum):
    boost = "boost"
    dampen = "dampen"
    debunk = "debunk"
    seed_opinion = "seed_opinion"
    weight_shift = "weight_shift"


class MetricName(StrEnum):
    """Canonical aggregate metric keys produced by :func:`hnle.metrics.summarize`.

    ``ModelSpec.metrics`` selects which of these keys are returned in the
    aggregate result. The values must stay identical to the keys in
    ``MetricSummary.to_dict``; ``tests/test_spec.py`` pins that contract.
    """

    diversity_final = "diversity_final"
    entropy_final = "entropy_final"
    polarization_final = "polarization_final"
    n_active_opinions = "n_active_opinions"
    assortativity = "assortativity"
    avg_share_final = "avg_share_final"
    time_to_consensus = "time_to_consensus"
    consensus_stability = "consensus_stability"
    absorbing = "absorbing"
    runaway = "runaway"
    cascade_p50 = "cascade_p50"
    cascade_p90 = "cascade_p90"
    cascade_p99 = "cascade_p99"
    cascade_max = "cascade_max"
    oscillation_zero_crossing_rate = "oscillation_zero_crossing_rate"
    oscillation_power_ratio = "oscillation_power_ratio"
    oscillation_dominant_freq = "oscillation_dominant_freq"
    oscillation_autocorr = "oscillation_autocorr"
    oscillation_sign_persistence = "oscillation_sign_persistence"
    oscillating = "oscillating"


def _all_metrics() -> list[MetricName]:
    """Return the default metric set with an explicit element type."""
    return list(MetricName)


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class LatencySpec(_Base):
    dist: LatencyDist = LatencyDist.normal
    mu: float = Field(5.0, gt=0)
    sigma: float = Field(2.0, gt=0)
    lam: float | None = Field(None, alias="lambda", gt=0)
    quantize: LatencyQuantize = LatencyQuantize.integer_steps

    @model_validator(mode="after")
    def _fill_lambda(self) -> Self:
        """Exponential latency: derive lambda from mu when not supplied."""
        if self.dist is LatencyDist.exponential and self.lam is None:
            object.__setattr__(self, "lam", 1.0 / self.mu)
        return self


class WeightsSpec(_Base):
    source: WeightSource = WeightSource.uniform
    normalize: WeightNormalize = WeightNormalize.max
    custom: dict[str, float] | None = None

    @model_validator(mode="after")
    def _check_custom(self) -> Self:
        if self.source is WeightSource.custom and not self.custom:
            raise ValueError(
                "weights.custom: must be a non-empty mapping when weights.source='custom'"
            )
        if self.custom is not None and any(value < 0 for value in self.custom.values()):
            raise ValueError("weights.custom: weights must be non-negative")
        return self


class TopologySpec(_Base):
    mode: TopologyMode = TopologyMode.static
    arrival_rate: float = Field(0.0, ge=0.0)
    decay_rate: float = Field(0.0, ge=0.0)


class HyperedgeSpec(_Base):
    min_size: int = Field(2, ge=2)
    max_size: int = Field(200, ge=2)

    @model_validator(mode="after")
    def _check_bounds(self) -> Self:
        if self.max_size < self.min_size:
            raise ValueError("hyperedge.max_size: must be greater than or equal to min_size")
        return self


class ShockSpec(_Base):
    at_step: int = Field(ge=0)
    type: ShockType
    magnitude: float = Field(ge=0.0, le=1.0)
    target: str | None = None
    duration: int = Field(1, ge=1)


class InterventionSpec(_Base):
    at_step: int = Field(ge=0)
    type: InterventionType
    target: dict[str, str] = Field(default_factory=dict)
    magnitude: float = Field(ge=0.0, le=1.0)
    duration: int = Field(ge=1, le=1000)


class ModelSpec(_Base):
    """Complete, validated simulation configuration."""

    engine: Engine = Engine.sparse_vector
    n_steps: int = Field(1000, ge=1, le=200_000)
    seed: int = Field(42, ge=0)
    repeats: int = Field(50, ge=1)

    q: float = Field(1.5, ge=0.01, le=20.0)
    decision_rule: DecisionRule = DecisionRule.stochastic
    threshold: float = Field(0.5, ge=0.0, le=1.0)
    init_mode: InitMode = InitMode.data_driven
    target_share_1: float = Field(0.5, ge=0.0, le=1.0)
    n_opinions: int = Field(2, ge=2, le=6)

    latency: LatencySpec = Field(default_factory=lambda: LatencySpec())
    weights: WeightsSpec = Field(default_factory=lambda: WeightsSpec())
    aggregation: Aggregation = Aggregation.mean
    topology: TopologySpec = Field(default_factory=lambda: TopologySpec())
    hyperedge: HyperedgeSpec = Field(default_factory=lambda: HyperedgeSpec())

    consensus_threshold: float = Field(0.8, ge=0.5, le=1.0)
    absorb_check: bool = True

    shocks: list[ShockSpec] = Field(default_factory=list)
    interventions: list[InterventionSpec] = Field(default_factory=list)
    metrics: list[MetricName] = Field(default_factory=_all_metrics)

    @model_validator(mode="after")
    def _check_engine_latency(self) -> Self:
        """The event kernel is defined for integer latency steps only."""
        if (
            self.engine is Engine.event_driven
            and self.latency.quantize is LatencyQuantize.continuous
        ):
            raise ValueError(
                "engine=event_driven requires latency.quantize='integer_steps'; "
                "use engine=sparse_vector for continuous latency"
            )
        return self

    @model_validator(mode="after")
    def _check_binary_only_controls(self) -> Self:
        """Shocks and interventions that assume two stances require k = 2."""
        binary_shocks = {ShockType.flip_share, ShockType.edge_boost}
        binary_interventions = {
            InterventionType.boost,
            InterventionType.dampen,
            InterventionType.debunk,
            InterventionType.weight_shift,
        }
        if self.n_opinions == 2:
            return self
        bad_shocks = [s.type.value for s in self.shocks if s.type in binary_shocks]
        bad_interventions = [
            i.type.value for i in self.interventions if i.type in binary_interventions
        ]
        if bad_shocks or bad_interventions:
            raise ValueError(
                "binary-only shocks/interventions require n_opinions=2; "
                f"got shocks={bad_shocks}, interventions={bad_interventions}"
            )
        return self

    def canonical_json(self) -> str:
        """Stable, key-sorted JSON used for hashing and equality checks."""
        payload = self.model_dump(mode="json", by_alias=True)
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def config_sha256(self) -> str:
        """Content hash of this spec, for run manifests."""
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def load_spec(path: str | Path) -> ModelSpec:
    """Load and validate a spec from a ``.yaml`` / ``.yml`` / ``.json`` file."""
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    suffix = p.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        raw: Any = yaml.safe_load(text)
    elif suffix == ".json":
        raw = json.loads(text)
    else:
        raise ValueError(f"unsupported spec extension {suffix!r}; expected .yaml/.yml/.json")
    if not isinstance(raw, dict):
        raise ValueError(f"spec file must contain a mapping at top level: {p}")
    return ModelSpec.model_validate(raw)


def save_spec(spec: ModelSpec, path: str | Path) -> None:
    """Write a spec back out as YAML or JSON (round-trips through load_spec)."""
    p = Path(path)
    payload = spec.model_dump(mode="json", by_alias=True)
    if p.suffix.lower() in {".yaml", ".yml"}:
        p.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    else:
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
