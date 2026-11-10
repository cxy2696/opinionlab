"""Engine dispatcher: choose the discrete CSR kernel or the event kernel."""

from __future__ import annotations

from hnle.core.event import run_event
from hnle.core.sparse import RunResult, run_sparse
from hnle.graph import Hypergraph
from hnle.spec import Engine, ModelSpec


def run_engine(spec: ModelSpec, graph: Hypergraph, seed: int) -> RunResult:
    """Run one replica with ``spec.engine``."""
    if spec.engine is Engine.event_driven:
        return run_event(spec, graph, seed)
    return run_sparse(spec, graph, seed)
