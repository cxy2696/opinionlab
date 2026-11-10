"""Group-level metrics.

Only aggregate statistics are allowed: per-node opinion trajectories are a
compliance red line (``NODE_TRACE_FORBIDDEN``), so every public function here
returns scalars (or fixed-size arrays of scalars) computed over the population.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np
import numpy.typing as npt

from hnle.spec import ModelSpec


def opinion_shares(
    opinions: npt.NDArray[np.int64], n_opinions: int | None = None
) -> npt.NDArray[np.float64]:
    """Fraction of nodes holding each opinion; always sums to 1."""
    if opinions.size == 0:
        raise ValueError("metrics.opinion_shares: opinions must be non-empty")
    k = n_opinions if n_opinions is not None else int(opinions.max()) + 1
    counts = np.bincount(opinions, minlength=k)[:k].astype(np.float64)
    return counts / opinions.size


def diversity(opinions: npt.NDArray[np.int64], n_opinions: int | None = None) -> float:
    """``1 - max_v share_v``: 0 for unanimity, ``1 - 1/k`` for a uniform k-way split."""
    shares = opinion_shares(opinions, n_opinions)
    return float(1.0 - shares.max())


def share(opinions: npt.NDArray[np.int64], opinion: int) -> float:
    """Fraction of nodes holding ``opinion``."""
    if opinions.size == 0:
        raise ValueError("metrics.share: opinions must be non-empty")
    return float(np.count_nonzero(opinions == opinion) / opinions.size)


def shannon_entropy(
    opinions: npt.NDArray[np.int64], n_opinions: int | None = None
) -> float:
    """Shannon entropy in bits: ``-sum_v p_v log2 p_v``."""
    shares = opinion_shares(opinions, n_opinions)
    positive = shares[shares > 0.0]
    return float(-np.sum(positive * np.log2(positive)))


def foster_polarization(
    opinions: npt.NDArray[np.int64], n_opinions: int | None = None
) -> float:
    """Normalised ``1 - sum_v p_v^2``: 0 for unanimity, 1 for a uniform split."""
    shares = opinion_shares(opinions, n_opinions)
    k = shares.size
    raw = 1.0 - float(np.sum(shares**2))
    maximum = 1.0 - 1.0 / k
    return raw / maximum if maximum > 0.0 else 0.0


def n_active_opinions(
    opinions: npt.NDArray[np.int64], n_opinions: int | None = None
) -> int:
    """Number of opinions with non-zero share."""
    shares = opinion_shares(opinions, n_opinions)
    return int(np.count_nonzero(shares > 0.0))


def assortativity(
    opinions: npt.NDArray[np.int64],
    hyperedges: tuple[tuple[int, ...], ...],
    n_opinions: int | None = None,
) -> float:
    """Opinion assortativity: observed same-opinion pair rate vs chance.

    ``(observed - expected) / (1 - expected)`` over all member pairs of all
    hyperedges; +1 when every hyperedge is homogeneous, 0 at chance level.
    """
    shares = opinion_shares(opinions, n_opinions)
    expected = float(np.sum(shares**2))
    total_pairs = 0
    same_pairs = 0
    for edge in hyperedges:
        members = np.asarray(edge, dtype=np.int64)
        size = members.size
        total_pairs += size * (size - 1) // 2
        counts = np.bincount(opinions[members], minlength=shares.size)
        same_pairs += int(np.sum(counts * (counts - 1) // 2))
    if total_pairs == 0 or expected >= 1.0:
        return 0.0
    observed = same_pairs / total_pairs
    return float((observed - expected) / (1.0 - expected))


def cascade_quantiles(cascade_series: list[float]) -> dict[str, float]:
    """p50 / p90 / p99 / max of the per-step cascade fraction."""
    if not cascade_series:
        return {"cascade_p50": 0.0, "cascade_p90": 0.0, "cascade_p99": 0.0, "cascade_max": 0.0}
    values = np.asarray(cascade_series, dtype=np.float64)
    p50, p90, p99 = np.percentile(values, [50.0, 90.0, 99.0])
    return {
        "cascade_p50": float(p50),
        "cascade_p90": float(p90),
        "cascade_p99": float(p99),
        "cascade_max": float(values.max()),
    }


def _detrend(series: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    if series.size < 2:
        if series.size == 0:
            return series
        return np.asarray(series - series.mean(), dtype=np.float64)
    x = np.arange(series.size, dtype=np.float64)
    slope, intercept = np.polyfit(x, series, 1)
    return np.asarray(series - (slope * x + intercept), dtype=np.float64)


def zero_crossing_rate(series: list[float]) -> float:
    """Sign changes per step of the detrended series."""
    values = _detrend(np.asarray(series, dtype=np.float64))
    if values.size < 2:
        return 0.0
    signs = values >= 0.0
    return float(np.count_nonzero(signs[1:] != signs[:-1]) / (values.size - 1))


def _highpass(series: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    """Remove slow trends with a centred moving average (keeps real cycles)."""
    if series.size < 8:
        return _detrend(series)
    window = max(3, series.size // 10)
    kernel = np.ones(window, dtype=np.float64) / window
    baseline = np.convolve(series, kernel, mode="same")
    return np.asarray(series - baseline, dtype=np.float64)


def fft_power_ratio(series: list[float]) -> float:
    """Power share of the dominant non-DC FFT bin after high-pass detrending."""
    values = _highpass(np.asarray(series, dtype=np.float64))
    if values.size < 4:
        return 0.0
    power = np.abs(np.fft.rfft(values)) ** 2
    total = float(power[1:].sum())
    if total <= 0.0:
        return 0.0
    return float(power[1:].max() / total)


def lag_autocorrelation(series: list[float], lag: int = 1) -> float:
    """Pearson autocorrelation of the detrended series at ``lag``."""
    values = _detrend(np.asarray(series, dtype=np.float64))
    if lag < 1 or values.size <= lag + 1:
        return 0.0
    left, right = values[:-lag], values[lag:]
    if left.std() == 0.0 or right.std() == 0.0:
        return 0.0
    return float(np.corrcoef(left, right)[0, 1])


def sign_persistence(series: list[float]) -> float:
    """Share of consecutive first-difference signs that agree (0..1)."""
    values = np.asarray(series, dtype=np.float64)
    if values.size < 3:
        return 0.0
    diffs = np.sign(np.diff(values))
    diffs = diffs[diffs != 0.0]
    if diffs.size < 2:
        return 0.0
    return float(np.count_nonzero(diffs[1:] == diffs[:-1]) / (diffs.size - 1))


def is_oscillating(series: list[float], threshold: float = 0.5) -> bool:
    """Synthetic-signal rule used by the tests and the report."""
    return fft_power_ratio(series) >= threshold


def time_to_consensus(diversity_series: list[float], consensus_threshold: float) -> int:
    """First index where ``1 - diversity`` reaches the threshold, else -1."""
    for step, value in enumerate(diversity_series):
        if 1.0 - value >= consensus_threshold:
            return step
    return -1


def consensus_stability(
    diversity_series: list[float], consensus_threshold: float, window: int
) -> bool:
    """True when consensus holds for ``window`` steps after first being reached."""
    reached = time_to_consensus(diversity_series, consensus_threshold)
    if reached < 0:
        return False
    end = reached + 1 + max(window, 0)
    if end > len(diversity_series):
        return False
    return all(1.0 - value >= consensus_threshold for value in diversity_series[reached:end])


@dataclass(frozen=True)
class MetricSummary:
    """Every scalar the report needs for one aggregated simulation."""

    diversity_final: float
    entropy_final: float
    polarization_final: float
    n_active_opinions: int
    assortativity: float
    avg_share_final: float
    time_to_consensus: int
    consensus_stability: float
    absorbing: bool
    runaway: bool
    cascade_p50: float
    cascade_p90: float
    cascade_p99: float
    cascade_max: float
    oscillation_zero_crossing_rate: float
    oscillation_power_ratio: float
    oscillation_dominant_freq: float
    oscillation_autocorr: float
    oscillation_sign_persistence: float
    oscillating: bool

    def to_dict(self) -> dict[str, float | int | bool]:
        return {
            "diversity_final": self.diversity_final,
            "entropy_final": self.entropy_final,
            "polarization_final": self.polarization_final,
            "n_active_opinions": self.n_active_opinions,
            "assortativity": self.assortativity,
            "avg_share_final": self.avg_share_final,
            "time_to_consensus": self.time_to_consensus,
            "consensus_stability": self.consensus_stability,
            "absorbing": self.absorbing,
            "runaway": self.runaway,
            "cascade_p50": self.cascade_p50,
            "cascade_p90": self.cascade_p90,
            "cascade_p99": self.cascade_p99,
            "cascade_max": self.cascade_max,
            "oscillation_zero_crossing_rate": self.oscillation_zero_crossing_rate,
            "oscillation_power_ratio": self.oscillation_power_ratio,
            "oscillation_dominant_freq": self.oscillation_dominant_freq,
            "oscillation_autocorr": self.oscillation_autocorr,
            "oscillation_sign_persistence": self.oscillation_sign_persistence,
            "oscillating": self.oscillating,
        }


def summarize(
    result: RunResultLike,
    spec: ModelSpec,
    hyperedges: tuple[tuple[int, ...], ...] | None = None,
) -> MetricSummary:
    """Compute the full metric set for one replica."""
    opinions = result.opinions
    k = spec.n_opinions
    reached = time_to_consensus(result.diversity_series, spec.consensus_threshold)
    window = int(np.ceil(result.max_latency))
    stable = consensus_stability(result.diversity_series, spec.consensus_threshold, window)
    quantiles = cascade_quantiles(result.cascade_series)
    oscillation = result.mean_opinion_series
    return MetricSummary(
        diversity_final=diversity(opinions, k),
        entropy_final=shannon_entropy(opinions, k),
        polarization_final=foster_polarization(opinions, k),
        n_active_opinions=n_active_opinions(opinions, k),
        assortativity=assortativity(opinions, hyperedges or (), k),
        avg_share_final=float(opinions.mean() / (k - 1)) if k > 1 else 0.0,
        time_to_consensus=reached,
        consensus_stability=1.0 if stable else 0.0,
        absorbing=stable,
        runaway=reached < 0,
        cascade_p50=quantiles["cascade_p50"],
        cascade_p90=quantiles["cascade_p90"],
        cascade_p99=quantiles["cascade_p99"],
        cascade_max=quantiles["cascade_max"],
        oscillation_zero_crossing_rate=zero_crossing_rate(oscillation),
        oscillation_power_ratio=fft_power_ratio(oscillation),
        oscillation_dominant_freq=_dominant_frequency(oscillation),
        oscillation_autocorr=lag_autocorrelation(oscillation, 1),
        oscillation_sign_persistence=sign_persistence(oscillation),
        oscillating=is_oscillating(oscillation),
    )


def _dominant_frequency(series: list[float], sample_rate: float = 1.0) -> float:
    values = _highpass(np.asarray(series, dtype=np.float64))
    if values.size < 4:
        return 0.0
    power = np.abs(np.fft.rfft(values)) ** 2
    index = int(np.argmax(power[1:])) + 1
    return float(index * sample_rate / values.size)


class RunResultLike(Protocol):
    """Structural type for :func:`summarize` (avoids a circular import)."""

    opinions: npt.NDArray[np.int64]
    diversity_series: list[float]
    cascade_series: list[float]
    mean_opinion_series: list[float]
    max_latency: float
