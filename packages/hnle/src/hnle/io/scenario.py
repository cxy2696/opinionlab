"""Scenario file loading: ModelSpec plus the graph it runs on."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import yaml  # type: ignore[import-untyped]

from hnle.graph import Hypergraph, random_hypergraph
from hnle.spec import ModelSpec


def load_scenario(path: str | Path) -> tuple[ModelSpec, Hypergraph, dict[str, Any]]:
    """Load ``{spec: ..., graph: ...}`` or a bare ModelSpec file."""
    payload: Any = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("scenario file must contain a mapping")
    spec_data = payload.get("spec", payload)
    graph_data = payload.get("graph") or {}
    spec = ModelSpec.model_validate(spec_data)

    n_nodes = int(graph_data.get("n_nodes", 200))
    n_edges = int(graph_data.get("n_edges", 400))
    graph_seed = int(graph_data.get("seed", spec.seed))
    rng = np.random.default_rng(graph_seed)
    initial = graph_data.get("initial_opinions")
    if initial is not None:
        graph = Hypergraph(
            n_nodes=len(initial),
            hyperedges=random_hypergraph(
                len(initial), n_edges, rng, spec.hyperedge
            ).hyperedges,
            initial_opinions=tuple(int(value) for value in initial),
        )
    else:
        graph = random_hypergraph(n_nodes, n_edges, rng, spec.hyperedge)
    return spec, graph, graph_data
