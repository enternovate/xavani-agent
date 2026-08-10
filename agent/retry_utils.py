# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Retry utilities — jittered backoff for decorrelated retries.

Replaces fixed exponential backoff with jittered delays to prevent
thundering-herd retry spikes when multiple sessions hit the same
rate-limited provider concurrently.
"""

import email.utils
import random
import threading
import time
from datetime import timezone
from typing import Any, Mapping, Optional

# Monotonic counter for jitter seed uniqueness within the same process.
# Protected by a lock to avoid race conditions in concurrent retry paths
# (e.g. multiple gateway sessions retrying simultaneously).
_jitter_counter = 0
_jitter_lock = threading.Lock()


def jittered_backoff(
    attempt: int,
    *,
    base_delay: float = 5.0,
    max_delay: float = 120.0,
    jitter_ratio: float = 0.5,
) -> float:
    """Compute a jittered exponential backoff delay.

    Args:
        attempt: 1-based retry attempt number.
        base_delay: Base delay in seconds for attempt 1.
        max_delay: Maximum delay cap in seconds.
        jitter_ratio: Fraction of computed delay to use as random jitter
            range.  0.5 means jitter is uniform in [0, 0.5 * delay].

    Returns:
        Delay in seconds: min(base * 2^(attempt-1), max_delay) + jitter.

    The jitter decorrelates concurrent retries so multiple sessions
    hitting the same provider don't all retry at the same instant.
    """
    global _jitter_counter
    with _jitter_lock:
        _jitter_counter += 1
        tick = _jitter_counter

    exponent = max(0, attempt - 1)
    if exponent >= 63 or base_delay <= 0:
        delay = max_delay
    else:
        delay = min(base_delay * (2 ** exponent), max_delay)

    # Seed from time + counter for decorrelation even with coarse clocks.
    seed = (time.time_ns() ^ (tick * 0x9E3779B9)) & 0xFFFFFFFF
    rng = random.Random(seed)
    jitter = rng.uniform(0, jitter_ratio * delay)

    return delay + jitter


def parse_retry_after(
    raw_value: Any,
    *,
    now: Optional[float] = None,
    max_delay: float = 120.0,
) -> Optional[float]:
    """Parse a Retry-After header value into a capped delay in seconds.

    Supports both RFC 7231 formats: delta-seconds (``"5"``) and HTTP-date
    (``"Wed, 21 Oct 2015 07:28:00 GMT"``).  Returns None when the value is
    missing, malformed, or negative so callers fall back to their own
    backoff policy instead of sleeping forever or not at all.
    """
    if raw_value is None:
        return None
    raw = str(raw_value).strip()
    if not raw:
        return None
    try:
        seconds = float(raw)
    except (TypeError, ValueError):
        seconds = None
    if seconds is None:
        try:
            when = email.utils.parsedate_to_datetime(raw)
        except (TypeError, ValueError, OverflowError):
            return None
        if when is None:
            return None
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        now_ts = time.time() if now is None else now
        seconds = when.timestamp() - now_ts
    if seconds < 0:
        return None
    return min(seconds, max_delay)


def rate_limit_backoff_delay(
    headers: Optional[Mapping[str, Any]],
    attempt: int,
    *,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    retry_after_cap: float = 120.0,
) -> float:
    """Delay before the next attempt after a 429.

    Uses the server's Retry-After header when present and parseable
    (capped at ``retry_after_cap``); otherwise falls back to jittered
    exponential backoff.
    """
    if headers is not None:
        raw = headers.get("retry-after") or headers.get("Retry-After")
        parsed = parse_retry_after(raw, max_delay=retry_after_cap)
        if parsed is not None:
            return parsed
    return jittered_backoff(attempt, base_delay=base_delay, max_delay=max_delay)
