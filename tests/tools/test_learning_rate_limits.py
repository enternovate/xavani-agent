# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""G10: learning rate limits tests."""

import pytest

import tools.learning_rate_limits as lrl
from tools.learning_rate_limits import (
    LearningRateLimiter,
    can_learn,
    learning_limiter,
    record_learning,
    reset_limiter,
)

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _clean():
    reset_limiter()
    yield
    reset_limiter()


# ── limiter math ───────────────────────────────────────────────────


def test_fresh_limiter_allows_learning():
    limiter = LearningRateLimiter(rate_per_hour=3)
    assert limiter.can_learn() is True


def test_cap_reached_blocks():
    limiter = LearningRateLimiter(rate_per_hour=3)
    assert limiter.record_learning() is True
    assert limiter.record_learning() is True
    assert limiter.record_learning() is True
    assert limiter.record_learning() is False
    assert limiter.can_learn() is False


def test_window_expires_events():
    limiter = LearningRateLimiter(rate_per_hour=2)
    now = 1_000_000.0
    assert limiter.record_learning(now=now) is True
    assert limiter.record_learning(now=now + 60) is True
    assert limiter.record_learning(now=now + 120) is False
    # Events older than 1h expire -> room returns.
    assert limiter.record_learning(now=now + 3700) is True


def test_events_in_window():
    limiter = LearningRateLimiter(rate_per_hour=5)
    limiter.record_learning()
    assert limiter.events_in_window() == 1


def test_reset_clears():
    limiter = LearningRateLimiter(rate_per_hour=1)
    limiter.record_learning()
    limiter.reset()
    assert limiter.can_learn() is True


def test_rate_clamped_to_one():
    limiter = LearningRateLimiter(rate_per_hour=0)
    assert limiter.rate_per_hour == 1


# ── module-level helpers ───────────────────────────────────────────


def test_record_learning_under_cap():
    reset_limiter()
    assert record_learning() is True


def test_cap_blocks_record():
    reset_limiter()
    import os

    os.environ["XAVANI_LEARN_RATE"] = "2"
    try:
        assert record_learning() is True
        assert record_learning() is True
        assert record_learning() is False
        assert can_learn() is False
    finally:
        os.environ.pop("XAVANI_LEARN_RATE", None)


def test_singleton():
    limiter1 = learning_limiter()
    limiter2 = learning_limiter()
    assert limiter1 is limiter2


def test_env_rate(monkeypatch):
    monkeypatch.setenv("XAVANI_LEARN_RATE", "7")
    reset_limiter()
    assert learning_limiter().rate_per_hour == 7


def test_bad_env_rate_falls_back(monkeypatch):
    monkeypatch.setenv("XAVANI_LEARN_RATE", "junk")
    reset_limiter()
    assert learning_limiter().rate_per_hour == lrl.DEFAULT_RATE_PER_HOUR
