"""Sparse engine entry point.

US-003 shipped a placeholder here; US-004 moved the real node-centric update
semantics into :mod:`hnle.core.update`. The CSR vectorised kernel (US-006)
will replace the internal probability computation behind the same signature.
"""

from __future__ import annotations

from hnle.core.update import RunResult, run_simulation
from hnle.graph import Hypergraph
from hnle.spec import ModelSpec

__all__ = ["RunResult", "run_sparse"]


def run_sparse(spec: ModelSpec, graph: Hypergraph, seed: int) -> RunResult:
    """Run one replica of the sparse engine."""
    return run_simulation(spec, graph, seed)
