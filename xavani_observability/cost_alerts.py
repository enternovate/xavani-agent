# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""D04: cost-per-minute spending guard.

Tracks the $/minute burn rate from recorded LLM call costs and alerts
when the rate exceeds a threshold. Runaway costs get discovered at the
bill today; this makes them visible in the moment.

Deterministic and thread-safe. Configurable via
XAVANI_COST_PER_MINUTE_ALERT (USD per minute, default 2.0).

Usage::

    from xavani_observability.cost_alerts import CostGuard, cost_guard

    guard = cost_guard()
    guard.record(cost_usd=0.05)
    if guard.burn_rate_per_minute() > guard.threshold:
        notify("cost burn rate exceeded")
"""

from __future__ import annotations

import os
import threading
import time
from typing import Dict, List, Optional

DEFAULT_THRESHOLD_USD_PER_MIN = 2.0
# 10-minute sliding window; one bucket per 30s.
_BUCKET_SECONDS = 30.0
_BUCKET_COUNT = 20


class CostGuard:
    """Sliding-window cost burn-rate tracker."""

    def __init__(self, threshold: float = DEFAULT_THRESHOLD_USD_PER_MIN):
        self.threshold = threshold
        self._lock = threading.Lock()
        self._buckets: List[tuple[float, float]] = []  # (start, cost_usd)

    def record(self, cost_usd: float, now: float | None = None) -> None:
        """Record the cost of one call."""
        if cost_usd <= 0:
            return
        now = now if now is not None else time.time()
        with self._lock:
            if not self._buckets or now - self._buckets[-1][0] >= _BUCKET_SECONDS:
                self._buckets.append((now, 0.0))
            start, total = self._buckets[-1]
            self._buckets[-1] = (start, total + cost_usd)
            self._prune(now)

    def _prune(self, now: float) -> None:
        cutoff = now - _BUCKET_SECONDS * _BUCKET_COUNT
        while self._buckets and self._buckets[0][0] < cutoff:
            self._buckets.pop(0)

    def burn_rate_per_minute(self, now: float | None = None) -> float:
        """USD per minute over the window. 0.0 when idle."""
        now = now if now is not None else time.time()
        with self._lock:
            self._prune(now)
            if not self._buckets:
                return 0.0
            window_start = self._buckets[0][0]
            total = sum(cost for _, cost in self._buckets)
            elapsed_min = max((now - window_start) / 60.0, 1e-6)
        return total / elapsed_min

    def exceeded(self, now: float | None = None) -> bool:
        """True when the burn rate is above the threshold."""
        return self.burn_rate_per_minute(now) > self.threshold

    def snapshot(self, now: float | None = None) -> Dict[str, float]:
        """Serializable view for dashboards and alerts."""
        rate = self.burn_rate_per_minute(now)
        with self._lock:
            total = sum(cost for _, cost in self._buckets)
        return {
            "burn_rate_usd_per_min": round(rate, 4),
            "threshold_usd_per_min": self.threshold,
            "window_total_usd": round(total, 4),
            "exceeded": rate > self.threshold,
        }


_guard: Optional[CostGuard] = None
_guard_lock = threading.Lock()


def configured_threshold() -> float:
    """Resolve the alert threshold from XAVANI_COST_PER_MINUTE_ALERT."""
    raw = os.environ.get("XAVANI_COST_PER_MINUTE_ALERT", "")
    if not raw:
        return DEFAULT_THRESHOLD_USD_PER_MIN
    try:
        return float(raw)
    except (TypeError, ValueError):
        return DEFAULT_THRESHOLD_USD_PER_MIN


def cost_guard() -> CostGuard:
    """Return the process-wide CostGuard (created lazily)."""
    global _guard
    with _guard_lock:
        if _guard is None:
            _guard = CostGuard(configured_threshold())
        return _guard


def record_call_cost(cost_usd: float) -> None:
    """Record a call cost into the process-wide guard (D04)."""
    try:
        cost_guard().record(cost_usd)
    except Exception:
        pass


def reset_cost_guard() -> None:
    """Reset the process-wide guard. For tests."""
    global _guard
    with _guard_lock:
        _guard = None
