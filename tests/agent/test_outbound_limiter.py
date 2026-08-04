# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""D12: outbound rate limiting tests."""

import time

import pytest

from agent.outbound_limiter import (
    TokenBucket,
    outbound_permit,
    outbound_release,
    reset_limiter,
    snapshot,
)


@pytest.fixture(autouse=True)
def _clean():
    reset_limiter()
    yield
    reset_limiter()


# ── token bucket ────────────────────────────────────────────────────


def test_bucket_full_at_start():
    b = TokenBucket(rate=1.0, burst=5)
    with b._lock:
        assert b._tokens == 5.0


def test_acquire_consumes_tokens():
    b = TokenBucket(rate=0.0, burst=10)  # no refill
    for _ in range(10):
        assert b.acquire(timeout=0.05) is True
    # Bucket empty and no refill — must fail fast.
    assert b.acquire(timeout=0.05) is False


def test_bucket_refills_over_time():
    b = TokenBucket(rate=10.0, burst=1)
    assert b.acquire(timeout=0.1) is True
    time.sleep(0.15)  # refills ~1.5 tokens at 10/s
    assert b.acquire(timeout=0.1) is True


def test_release_token_returns_burst_capped():
    b = TokenBucket(rate=0.0, burst=3)
    b.acquire(timeout=0.1)
    b.release_token()
    with b._lock:
        assert b._tokens == 3.0


# ── global permit API ───────────────────────────────────────────────


def test_outbound_permit_acquire_release():
    assert outbound_permit("anthropic", timeout=1.0) is True
    outbound_release("anthropic")


def test_provider_rate_limits_calls():
    reset_limiter()
    # Slow provider: 1 rps, burst 20 (DEFAULT_BURST).
    import agent.outbound_limiter as ol

    ol._PROVIDER_DEFAULT_RPS["slowpoke"] = 1.0
    try:
        acquired = 0
        for _ in range(25):
            if outbound_permit("slowpoke", timeout=0.05):
                acquired += 1
                outbound_release("slowpoke")
            else:
                break
        # Burst (20) is acquirable; sustained calls beyond burst are
        # rate-limited by the 1 rps refill.
        assert acquired >= 20
        assert acquired < 25
    finally:
        ol._PROVIDER_DEFAULT_RPS.pop("slowpoke", None)


def test_global_concurrency_cap():
    reset_limiter()
    import agent.outbound_limiter as ol

    # Exhaust the global semaphore.
    for _ in range(ol.DEFAULT_GLOBAL_MAX_CONCURRENT):
        assert outbound_permit("fast", timeout=0.1) is True
    # One more must be rejected by the concurrency cap.
    assert outbound_permit("fast", timeout=0.1) is False
    for _ in range(ol.DEFAULT_GLOBAL_MAX_CONCURRENT):
        outbound_release("fast")
    assert outbound_permit("fast", timeout=0.1) is True
    outbound_release("fast")


def test_env_rate_override(monkeypatch):
    reset_limiter()
    monkeypatch.setenv("XAVANI_OUTBOUND_RPS_CUSTOM", "50")
    import agent.outbound_limiter as ol

    assert ol._resolve_rate("custom") == 50.0


def test_snapshot_untouched_provider():
    assert snapshot("never-used") is None


def test_snapshot_shape():
    assert outbound_permit("snap", timeout=0.1) is True
    snap = snapshot("snap")
    assert snap is not None
    assert snap["rate"] > 0
    assert snap["burst"] >= 1
    outbound_release("snap")
