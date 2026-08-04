"""Anomaly detection for time-series metrics (E03).

Pure-function detector: flag values that deviate more than ``sigma``
standard deviations from the rolling mean of a trailing window. Used by
operators to spot cost spikes, error bursts, and latency outliers without
a model call.
"""

from __future__ import annotations

import math
import statistics
from typing import List, Optional


def detect_anomalies(
    values: List[float],
    *,
    window: int = 20,
    sigma: float = 3.0,
    min_samples: int = 5,
) -> List[int]:
    """Return the indices of anomalous values in *values*.

    Each index is scored against the mean/std of the trailing window of
    up to *window* previous values (values before the current index).
    A value is anomalous when |z| > sigma. Windows smaller than
    ``min_samples`` produce no verdict (return nothing for those indices)
    because a mean of 1-2 points is meaningless.

    Pure function — no IO, no state, deterministic.
    """
    if not values or window < 2:
        return []
    if sigma <= 0:
        raise ValueError("sigma must be positive")
    anomalies: List[int] = []
    for i, value in enumerate(values):
        if i < min_samples:
            continue
        window_start = max(0, i - window)
        window_values = values[window_start:i]
        if len(window_values) < min_samples:
            continue
        try:
            mean = statistics.fmean(window_values)
            stdev = statistics.stdev(window_values) if len(window_values) > 1 else 0.0
        except statistics.StatisticsError:
            continue
        if stdev <= 0:
            # Zero-variance window: any deviation from the constant mean is
            # unboundedly anomalous (a spike against a flat baseline).
            if value != mean:
                anomalies.append(i)
            continue
        z = abs(float(value) - mean) / stdev
        if z > sigma:
            anomalies.append(i)
    return anomalies


def detect_spike(
    values: List[float],
    *,
    window: int = 20,
    sigma: float = 3.0,
    min_samples: int = 5,
) -> Optional[int]:
    """Return the index of the single most anomalous spike, if any."""
    anomalies = detect_anomalies(values, window=window, sigma=sigma, min_samples=min_samples)
    if not anomalies:
        return None
    # Return the most recent anomaly — the one an operator should look at now.
    return anomalies[-1]


__all__ = ["detect_anomalies", "detect_spike"]
