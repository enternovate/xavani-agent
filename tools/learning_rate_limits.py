# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""G10: learning rate limits.

Caps how much the system may learn in a window. Learning (new
preferences, new continuations, new schedule entries, capability
updates) is cheap individually, but unbounded accumulation becomes
noise. The rate limiter is a token bucket for LEARNING EVENTS per
window — when the bucket is empty, new learning is deferred (the
caller decides what deferral means).

Deterministic and thread-safe. Configurable via
XAVANI_LEARN_RATE (events per hour, default 60).

Usage::

    from tools.learning_rate_limits import can_learn, record_learning

    if can_learn():
        record_learning()
        learn(...)
"""

from __future__ import annotations

import os
import threading
import time
from typing import Dict, Optional

DEFAULT_RATE_PER_HOUR = 60
_BUCKET_SECONDS = 3600.0  # 1-hour window


class LearningRateLimiter:
    """Per-window learning event limiter (thread-safe)."""

    def __init__(self, rate_per_hour: int = DEFAULT_RATE_PER_HOUR):
        self.rate_per_hour = max(1, rate_per_hour)
        self._lock = threading.Lock()
        self._events: list = []  # timestamps

    def _prune(self, now: float) -> None:
        cutoff = now - _BUCKET_SECONDS
        while self._events and self._events[0] < cutoff:
            self._events.pop(0)

    def can_learn(self, now: float | None = None) -> bool:
        now = now if now is not None else time.time()
        with self._lock:
            self._prune(now)
            return len(self._events) < self.rate_per_hour

    def record_learning(self, now: float | None = None) -> bool:
        """Record one learning event. True when accepted under the cap."""
        now = now if now is not None else time.time()
        with self._lock:
            self._prune(now)
            if len(self._events) >= self.rate_per_hour:
                return False
            self._events.append(now)
            return True

    def events_in_window(self, now: float | None = None) -> int:
        now = now if now is not None else time.time()
        with self._lock:
            self._prune(now)
            return len(self._events)

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


_limiter: Optional[LearningRateLimiter] = None
_limiter_lock = threading.Lock()


def _configured_rate() -> int:
    raw = os.environ.get("XAVANI_LEARN_RATE", str(DEFAULT_RATE_PER_HOUR))
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return DEFAULT_RATE_PER_HOUR


def learning_limiter() -> LearningRateLimiter:
    """Return the process-wide learning limiter."""
    global _limiter
    with _limiter_lock:
        if _limiter is None:
            _limiter = LearningRateLimiter(_configured_rate())
        return _limiter


def can_learn() -> bool:
    """True when a new learning event fits the current window."""
    try:
        return learning_limiter().can_learn()
    except Exception:
        return True  # limiter failure must not block learning


def record_learning() -> bool:
    """Record a learning event. True when accepted under the cap."""
    try:
        return learning_limiter().record_learning()
    except Exception:
        return True


def reset_limiter() -> None:
    """Reset the process-wide limiter. For tests."""
    global _limiter
    with _limiter_lock:
        _limiter = None
