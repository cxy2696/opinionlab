"""Run manifests: hashes, versions and reproducibility.

A manifest records everything needed to rebuild a run: the canonical spec, the
graph arrays, the seed, tool versions and the git commit. ``run_id`` is derived
from ``config_sha256 + seed`` so identical work is addressable and de-duplicated.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt

import hnle
from hnle.graph import Hypergraph
from hnle.spec import ModelSpec


def git_sha() -> str:
    """Best-effort git commit for provenance; never fails a run."""
    env = os.environ.get("GIT_SHA")
    if env:
        return env
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def package_versions() -> dict[str, str]:
    import pandas as pd
    import scipy

    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "pandas": pd.__version__,
        "engine": hnle.__version__,
    }


def graph_sha256(
    graph: Hypergraph, weights: npt.NDArray[np.float64] | None = None
) -> str:
    """Hash the canonical graph arrays (order already canonical)."""
    digest = hashlib.sha256()
    digest.update(f"n={graph.n_nodes}".encode())
    for edge in graph.hyperedges:
        digest.update(b"|")
        digest.update(",".join(str(node) for node in edge).encode())
    if graph.initial_opinions is not None:
        digest.update(b"|init:")
        digest.update(np.asarray(graph.initial_opinions, dtype=np.int64).tobytes())
    if weights is not None:
        digest.update(b"|w:")
        digest.update(np.asarray(weights, dtype=np.float64).tobytes())
    return digest.hexdigest()


def run_id_for(spec: ModelSpec) -> str:
    """Filesystem-safe, addressable id derived from config hash and seed."""
    return f"{spec.config_sha256()[:16]}-{spec.seed}"


def build_manifest(
    spec: ModelSpec,
    graph: Hypergraph,
    weights: npt.NDArray[np.float64],
    *,
    wall_clock_seconds: float,
    artifacts: dict[str, str] | None = None,
) -> dict[str, Any]:
    return {
        "run_id": run_id_for(spec),
        "config_sha256": spec.config_sha256(),
        "data_sha256": graph_sha256(graph, weights),
        "git_sha": git_sha(),
        "spec": spec.model_dump(mode="json", by_alias=True),
        "seed": spec.seed,
        "repeats": spec.repeats,
        "engine_version": hnle.__version__,
        "versions": package_versions(),
        "wall_clock_seconds": round(wall_clock_seconds, 6),
        "cpu_count": os.cpu_count() or 1,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "artifacts": artifacts or {},
    }


def write_manifest(path: str | Path, manifest: dict[str, Any]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def load_manifest(path: str | Path) -> dict[str, Any]:
    payload: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
    return payload


def spec_from_manifest(manifest: dict[str, Any]) -> ModelSpec:
    return ModelSpec.model_validate(manifest["spec"])


def save_graph(
    path: str | Path,
    graph: Hypergraph,
    weights: npt.NDArray[np.float64],
) -> Path:
    lengths = np.asarray([len(edge) for edge in graph.hyperedges], dtype=np.int64)
    pointer = np.concatenate([[0], np.cumsum(lengths)]).astype(np.int64)
    flat = np.asarray([node for edge in graph.hyperedges for node in edge], dtype=np.int64)
    initial = (
        np.asarray(graph.initial_opinions, dtype=np.int64)
        if graph.initial_opinions is not None
        else np.asarray([], dtype=np.int64)
    )
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        target,
        n_nodes=np.asarray([graph.n_nodes], dtype=np.int64),
        edge_ptr=pointer,
        edge_nodes=flat,
        initial=initial,
        weights=np.asarray(weights, dtype=np.float64),
    )
    return target


def load_graph(path: str | Path) -> tuple[Hypergraph, npt.NDArray[np.float64]]:
    with np.load(Path(path)) as data:
        n_nodes = int(data["n_nodes"][0])
        pointer = data["edge_ptr"]
        flat = data["edge_nodes"]
        edges = tuple(
            tuple(int(node) for node in flat[pointer[i] : pointer[i + 1]])
            for i in range(len(pointer) - 1)
        )
        initial = data["initial"]
        weights = np.asarray(data["weights"], dtype=np.float64)
    return (
        Hypergraph(
            n_nodes=n_nodes,
            hyperedges=edges,
            initial_opinions=tuple(int(v) for v in initial) if initial.size else None,
            weights=tuple(float(v) for v in weights),
        ),
        weights,
    )


def reproduce(manifest_path: str | Path) -> tuple[Any, ModelSpec]:
    """Rebuild a run from its manifest and stored graph arrays."""
    from hnle.engine import run_engine

    manifest = load_manifest(manifest_path)
    spec = spec_from_manifest(manifest)
    graph_path = Path(manifest_path).parent / "graph.npz"
    graph, _weights = load_graph(graph_path)
    return run_engine(spec, graph, spec.seed), spec


def system_summary() -> dict[str, str]:
    return {"platform": sys.platform, **package_versions()}
