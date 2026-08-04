# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""D12: rate limiting on outbound API calls.

Global concurrency cap + per-provider token-bucket rate limiting for
outbound HTTP calls. Callers acquire a permit before opening a socket;
when the bucket is empty the call waits (bounded) instead of slamming
the provider and getting banned.

Deterministic, thread-safe, zero config by default (limits only apply
when configured via XAVANI_OUTBOUND_RPS_<PROVIDER> or the registry
defaults).

Usage::

    from agent.outbound_limiter import outbound_permit

    with outbound_permit("anthropic"):
        resp = client.chat.completions.create(...)
"""

from __future__ import annotations

import os
import threading
import time
from typing import Dict, Optional

DEFAULT_GLOBAL_MAX_CONCURRENT = 8
DEFAULT_RPS = 10.0          # default permits per second per provider
DEFAULT_BURST = 20          # bucket capacity (burst allowance)

# Per-provider default RPS overrides (opt-in via env or defaults below).
_PROVIDER_DEFAULT_RPS: Dict[str, float] = {
    "anthropic": 5.0,
    "openai": 10.0,
    "openrouter": 10.0,
}

_global_semaphore = threading.BoundedSemaphore(DEFAULT_GLOBAL_MAX_CONCURRENT)


class TokenBucket:
    """A simple thread-safe token bucket."""

    def __init__(self, rate: float, burst: int):
        self.rate = rate
        self.burst = burst
        self._tokens = float(burst)
        self._last = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self, timeout: float = 10.0) -> bool:
        """Block until a token is available or the timeout expires.

        Returns True when a token was acquired (caller may proceed).
        """
        deadline = time.monotonic() + timeout
        while True:
            with self._lock:
                now = time.monotonic()
                self._tokens = min(
                    self.burst,
                    self._tokens + (now - self._last) * self.rate,
                )
                self._last = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.05)

    def release_token(self) -> None:
        """Give one token back (used when the global cap rejects)."""
        with self._lock:
            self._tokens = min(self.burst, self._tokens + 1.0)


_buckets: Dict[str, TokenBucket] = {}
_buckets_lock = threading.Lock()


def _resolve_rate(provider: str) -> float:
    env = os.environ.get(f"XAVANI_OUTBOUND_RPS_{provider.upper().replace('-', '_')}")
    if env:
        try:
            return float(env)
        except (TypeError, ValueError):
            pass
    return _PROVIDER_DEFAULT_RPS.get(provider, DEFAULT_RPS)


def outbound_permit(provider: str, timeout: float = 10.0) -> bool:
    """Acquire the global concurrency slot AND a provider token.

    Returns True when the caller may proceed. Callers MUST pair this
    with :func:`outbound_release` when True.
    """
    bucket = _bucket_for(provider)
    if not bucket.acquire(timeout=timeout):
        return False
    if not _global_semaphore.acquire(blocking=False):
        # Concurrency cap reached — release the token and fail fast so
        # the caller can retry or shed load instead of queueing forever.
        bucket.release_token()
        return False
    return True


def outbound_release(provider: str) -> None:
    """Release the permit acquired by :func:`outbound_permit`."""
    _global_semaphore.release()
    # The token-bucket token was already consumed; nothing else to do.
    # (Kept as a paired API so callers always release exactly once.)


def _bucket_for(provider: str) -> TokenBucket:
    with _buckets_lock:
        bucket = _buckets.get(provider)
        if bucket is None:
            bucket = TokenBucket(_resolve_rate(provider), DEFAULT_BURST)
            _buckets[provider] = bucket
        return bucket


def reset_limiter() -> None:
    """Reset all buckets and the global semaphore. For tests."""
    global _global_semaphore
    with _buckets_lock:
        _buckets.clear()
    _global_semaphore = threading.BoundedSemaphore(DEFAULT_GLOBAL_MAX_CONCURRENT)


def snapshot(provider: str) -> Optional[Dict[str, float]]:
    """Current bucket state for a provider (None when untouched)."""
    with _buckets_lock:
        bucket = _buckets.get(provider)
    if bucket is None:
        return None
    with bucket._lock:
        return {
            "rate": bucket.rate,
            "burst": bucket.burst,
            "tokens": round(bucket._tokens, 2),
        }
