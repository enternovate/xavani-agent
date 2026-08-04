# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""E06: error budget tracking per subsystem.

Each subsystem declares an SLO (availability target). Errors consume
budget; success over time replenishes it. The tracker reports:

- current availability (rolling window)
- budget remaining (percentage)
- violated (bool) — when availability fell below the SLO

Trackers are pure counters — recording is O(1) and thread-safe. The
window is a fixed-size ring of 1-minute buckets, so memory stays
bounded regardless of runtime.

Usage::

    from xavani_observability.error_budget import ErrorBudget, SUBSYSTEM_SLOS

    budget = ErrorBudget("gateway", slo=0.999)
    budget.record(success=True)
    if budget.violated():
        alert(f"gateway error budget exhausted: {budget.summary()}")
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional

# Default SLOs per subsystem (brainstorm E06: gateway 99.9%, agent
# 99.5%, tools 99%). Expressed as fractions of successful operations.
SUBSYSTEM_SLOS: Dict[str, float] = {
    "gateway": 0.999,
    "agent": 0.995,
    "tools": 0.99,
    "cron": 0.99,
}

# One bucket per minute; 60 buckets = 1-hour rolling window.
_BUCKET_SECONDS = 60.0
_BUCKET_COUNT = 60

# Process-wide singleton feeding from the metrics collector.
_tool_budgets: Optional["ErrorBudget"] = None
_tool_budgets_lock = threading.Lock()


def record_tool_outcome(success: bool) -> None:
    """Record a tool outcome into the process-wide tools budget (E06)."""
    global _tool_budgets
    with _tool_budgets_lock:
        if _tool_budgets is None:
            _tool_budgets = ErrorBudget("tools")
        _tool_budgets.record(success)


def get_tool_budget() -> "ErrorBudget":
    """Return the process-wide tools error budget (creating it lazily)."""
    global _tool_budgets
    with _tool_budgets_lock:
        if _tool_budgets is None:
            _tool_budgets = ErrorBudget("tools")
        return _tool_budgets


class ErrorBudget:
    """Rolling-window error budget for one subsystem."""

    def __init__(self, subsystem: str, slo: Optional[float] = None):
        self.subsystem = subsystem
        self.slo = slo if slo is not None else SUBSYSTEM_SLOS.get(subsystem, 0.99)
        self._lock = threading.Lock()
        # Ring of (bucket_start, success_count, failure_count).
        self._buckets: list[tuple[float, int, int]] = []

    def _prune(self, now: float) -> None:
        cutoff = now - _BUCKET_SECONDS * _BUCKET_COUNT
        while self._buckets and self._buckets[0][0] < cutoff:
            self._buckets.pop(0)

    def record(self, success: bool, now: float | None = None) -> None:
        """Record one operation outcome."""
        now = now if now is not None else time.time()
        with self._lock:
            if not self._buckets or now - self._buckets[-1][0] >= _BUCKET_SECONDS:
                self._buckets.append((now, 0, 0))
            bucket = self._buckets[-1]
            if success:
                self._buckets[-1] = (bucket[0], bucket[1] + 1, bucket[2])
            else:
                self._buckets[-1] = (bucket[0], bucket[1], bucket[2] + 1)
            self._prune(now)

    def _totals(self) -> tuple[int, int]:
        with self._lock:
            success = sum(b[1] for b in self._buckets)
            failure = sum(b[2] for b in self._buckets)
        return success, failure

    def availability(self) -> Optional[float]:
        """Return window availability (0..1), or None with no data."""
        success, failure = self._totals()
        total = success + failure
        if total == 0:
            return None
        return success / total

    def budget_remaining(self) -> Optional[float]:
        """Return remaining budget fraction (1.0 = full). None when idle."""
        availability = self.availability()
        if availability is None:
            return None
        # Budget is consumed when availability drops below the SLO.
        # Surplus above the SLO is capped at 1.0 (full budget).
        if self.slo <= 0:
            return 0.0
        return min(1.0, availability / self.slo)

    def violated(self) -> bool:
        """True when window availability fell below the SLO."""
        availability = self.availability()
        if availability is None:
            return False
        return availability < self.slo

    def summary(self) -> Dict[str, Any]:
        """Return a serializable snapshot for dashboards and alerts."""
        success, failure = self._totals()
        availability = self.availability()
        remaining = self.budget_remaining()
        return {
            "subsystem": self.subsystem,
            "slo": self.slo,
            "success_count": success,
            "failure_count": failure,
            "total_count": success + failure,
            "availability": round(availability, 6) if availability is not None else None,
            "budget_remaining": round(remaining, 6) if remaining is not None else None,
            "violated": self.violated(),
        }
