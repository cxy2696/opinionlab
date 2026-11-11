"""Shared mathematical kernel for every engine.

The dense reference, the CSR kernel and the event kernel must agree on the
conformity map, the ordinal mean opinion and the consensus test. Keeping those
three operations here removes duplicated formulas and makes divergence a test
failure rather than a silent numerical difference.

All functions assume non-negative weighted counts. Node weights are validated
as non-negative in :mod:`hnle.spec` and :mod:`hnle.core.update`.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt


def conformity_probabilities(
    scores: npt.NDArray[np.float64], q: float
) -> tuple[npt.NDArray[np.float64], int]:
    """Map weighted opinion counts to a probability vector per hyperedge.

    ``scores`` has shape ``(..., k)``. For ``q > 0`` a stance with zero score
    receives zero mass; an edge whose total score is zero falls back to the
    uniform distribution and is counted in the returned ``zero_edges`` value.
    ``q = 0`` is rejected: at ``q = 0`` the limit depends on which stances are
    present, and numpy's ``0**0 = 1`` convention would assign mass to absent
    stances.
    """
    if not np.isfinite(q) or q <= 0.0:
        raise ValueError("q must be finite and strictly positive")
    values = np.asarray(scores, dtype=np.float64)
    if values.size == 0:
        return values.copy(), 0
    if np.any(values < 0.0):
        raise ValueError("weighted counts must be non-negative")
    k = values.shape[-1]
    powered = np.power(values, q)
    denominator = powered.sum(axis=-1, keepdims=True)
    uniform = np.full(values.shape, 1.0 / k, dtype=np.float64)
    probabilities = np.divide(
        powered,
        denominator,
        out=uniform.copy(),
        where=denominator > 0.0,
    )
    zero_edges = int(np.count_nonzero(denominator <= 0.0))
    return np.asarray(probabilities, dtype=np.float64), zero_edges


def normalize_rows(probabilities: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    """Renormalise each row to sum to one; all-zero rows stay zero.

    Used by the ``max`` aggregation, which is an element-wise maximum of
    distributions and is therefore not itself a distribution until it is
    renormalised.
    """
    values = np.asarray(probabilities, dtype=np.float64)
    totals = values.sum(axis=-1, keepdims=True)
    return np.asarray(
        np.divide(values, totals, out=np.zeros_like(values), where=totals > 0.0),
        dtype=np.float64,
    )


def ordinal_mean_opinion(
    opinions: npt.NDArray[np.int64], n_opinions: int
) -> float:
    """Mean stance on the ordinal scale ``0, ..., k-1`` rescaled to ``[0, 1]``.

    This is the share of opinion 1 when ``k = 2``. For ``k > 2`` it assumes the
    stance labels are ordered and equally spaced; the full share vector is
    reported separately by :func:`hnle.metrics.opinion_shares`.
    """
    if n_opinions <= 1:
        return 0.0
    return float(np.mean(opinions) / (n_opinions - 1))


def reached_consensus(
    opinions: npt.NDArray[np.int64], n_opinions: int, threshold: float
) -> bool:
    """Whether the largest stance share is at least ``threshold``."""
    if opinions.size == 0:
        raise ValueError("opinions must be non-empty")
    counts = np.bincount(opinions, minlength=n_opinions)
    return bool(counts.max() / opinions.size >= threshold)
