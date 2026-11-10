"""Group-level metrics (PRD OPT-30..34).

Only aggregate statistics are allowed: per-node opinion trajectories are a
compliance red line (``NODE_TRACE_FORBIDDEN``), so every function here returns
scalars computed over the whole population.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt


def diversity(opinions: npt.NDArray[np.int64]) -> float:
    """``1 - max_v share_v``: 0 for unanimity, ``1 - 1/k`` for a uniform k-way split."""
    if opinions.size == 0:
        raise ValueError("metrics.diversity: opinions must be non-empty")
    counts = np.bincount(opinions)
    return float(1.0 - counts.max() / opinions.size)


def share(opinions: npt.NDArray[np.int64], opinion: int) -> float:
    """Fraction of nodes holding ``opinion``."""
    if opinions.size == 0:
        raise ValueError("metrics.share: opinions must be non-empty")
    return float(np.count_nonzero(opinions == opinion) / opinions.size)
