"""External shocks, interventions and time-varying topology (PRD OPT-23/35).

Shocks are one-shot events at a given step; interventions act over a window.
Both only touch aggregate state (opinions/probabilities), never per-node
traces, so the compliance rule on node trajectories still holds.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from hnle.spec import InterventionType, ModelSpec, ShockType, TopologyMode


def apply_one_shot(
    spec: ModelSpec,
    opinions: npt.NDArray[np.int64],
    step: int,
    rng: np.random.Generator,
) -> npt.NDArray[np.bool_]:
    """Apply shocks / seed interventions scheduled exactly at ``step``."""
    n_nodes = opinions.size
    changed = np.zeros(n_nodes, dtype=np.bool_)

    for shock in spec.shocks:
        if shock.at_step != step:
            continue
        count = int(round(shock.magnitude * n_nodes))
        if count <= 0:
            continue
        if shock.type is ShockType.flip_share:
            chosen = rng.choice(n_nodes, size=min(count, n_nodes), replace=False)
            opinions[chosen] = 1 - opinions[chosen]
            changed[chosen] = True
        elif shock.type is ShockType.new_opinion:
            chosen = rng.choice(n_nodes, size=min(count, n_nodes), replace=False)
            opinions[chosen] = rng.integers(0, spec.n_opinions, size=chosen.size)
            changed[chosen] = True
        # edge_boost is expressed as a temporary probability bias below

    for intervention in spec.interventions:
        if intervention.at_step != step:
            continue
        count = int(round(intervention.magnitude * n_nodes))
        if count <= 0:
            continue
        if intervention.type is InterventionType.debunk:
            candidates = np.nonzero(opinions == 0)[0]
            if candidates.size:
                chosen = rng.choice(candidates, size=min(count, candidates.size), replace=False)
                opinions[chosen] = 1
                changed[chosen] = True
        elif intervention.type is InterventionType.seed_opinion:
            target = int(intervention.target.get("opinion", 1))
            target = max(0, min(target, spec.n_opinions - 1))
            candidates = np.nonzero(opinions != target)[0]
            if candidates.size:
                chosen = rng.choice(candidates, size=min(count, candidates.size), replace=False)
                opinions[chosen] = target
                changed[chosen] = True

    return changed


def probability_bias(spec: ModelSpec, step: int) -> float:
    """Additive bias to P(opinion=1) from active boost/dampen interventions."""
    bias = 0.0
    for intervention in spec.interventions:
        if not (intervention.at_step <= step < intervention.at_step + intervention.duration):
            continue
        if intervention.type is InterventionType.boost:
            bias += intervention.magnitude
        elif intervention.type is InterventionType.dampen:
            bias -= intervention.magnitude
        elif intervention.type is InterventionType.weight_shift:
            bias += intervention.magnitude * 0.5
    for shock in spec.shocks:
        if shock.at_step == step and shock.type is ShockType.edge_boost:
            bias += shock.magnitude
    return bias


def evolve_topology(
    spec: ModelSpec,
    edges: list[tuple[int, ...]],
    n_nodes: int,
    rng: np.random.Generator,
) -> tuple[list[tuple[int, ...]], int, int]:
    """Grow/decay the hyperedge list for ``topology.mode=time_varying``."""
    if spec.topology.mode is not TopologyMode.time_varying:
        return edges, 0, 0
    added = 0
    removed = 0
    if spec.topology.arrival_rate > 0.0:
        arrivals = int(rng.poisson(spec.topology.arrival_rate))
        for _ in range(arrivals):
            size = int(rng.integers(spec.hyperedge.min_size, spec.hyperedge.max_size + 1))
            size = min(size, n_nodes)
            members = rng.choice(n_nodes, size=size, replace=False)
            edges.append(tuple(sorted(int(node) for node in members)))
            added += 1
    if spec.topology.decay_rate > 0.0 and edges:
        drop = int(round(spec.topology.decay_rate * len(edges)))
        if drop > 0:
            drop = min(drop, len(edges))
            indices = set(rng.choice(len(edges), size=drop, replace=False).tolist())
            edges = [edge for index, edge in enumerate(edges) if index not in indices]
            removed = drop
    return edges, added, removed
