"""shared kernel: conformity map, normalisation, ordinal mean, consensus."""

from __future__ import annotations

import numpy as np
import pytest

from hnle.core.kernel import (
    conformity_probabilities,
    normalize_rows,
    ordinal_mean_opinion,
    reached_consensus,
)


def test_conformity_at_q_one_is_weighted_share() -> None:
    scores = np.array([[1.0, 3.0], [0.0, 2.0]])
    probs, zero = conformity_probabilities(scores, 1.0)
    np.testing.assert_allclose(probs, [[0.25, 0.75], [0.0, 1.0]])
    assert zero == 0


def test_absent_stance_has_zero_mass_for_positive_q() -> None:
    probs, _ = conformity_probabilities(np.array([[0.0, 2.0, 0.0]]), 1.5)
    np.testing.assert_allclose(probs, [[0.0, 1.0, 0.0]])


def test_zero_edge_falls_back_to_uniform() -> None:
    probs, zero = conformity_probabilities(np.array([[0.0, 0.0], [1.0, 1.0]]), 2.0)
    np.testing.assert_allclose(probs[0], [0.5, 0.5])
    assert zero == 1


def test_q_zero_is_rejected() -> None:
    with pytest.raises(ValueError):
        conformity_probabilities(np.array([[1.0, 1.0]]), 0.0)


def test_negative_counts_are_rejected() -> None:
    with pytest.raises(ValueError):
        conformity_probabilities(np.array([[-1.0, 2.0]]), 1.0)


def test_normalize_rows_handles_zero_rows() -> None:
    values = np.array([[1.0, 3.0], [0.0, 0.0]])
    normalized = normalize_rows(values)
    np.testing.assert_allclose(normalized[0], [0.25, 0.75])
    np.testing.assert_allclose(normalized[1], [0.0, 0.0])
    np.testing.assert_allclose(normalized[0].sum(), 1.0)


def test_ordinal_mean_opinion() -> None:
    assert ordinal_mean_opinion(np.array([0, 1]), 2) == 0.5
    assert ordinal_mean_opinion(np.array([0, 1, 2]), 3) == 0.5
    assert ordinal_mean_opinion(np.array([1, 1]), 2) == 1.0


def test_reached_consensus_uses_largest_share() -> None:
    opinions = np.array([0, 0, 0, 1])
    assert reached_consensus(opinions, 2, 0.75)
    assert not reached_consensus(opinions, 2, 0.8)
