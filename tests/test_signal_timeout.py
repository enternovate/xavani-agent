# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the reusable signal-based timeout guard (D15).

``signal_timeout(seconds, description)`` in tests/conftest.py wraps any
blocking operation in a SIGALRM deadline.  On expiry it raises TimeoutError
naming the operation, instead of hanging the whole suite.  The autouse
30-second test timeout is built on the same guard.
"""

import signal
import time

import pytest

from tests.conftest import signal_timeout

pytestmark = pytest.mark.skipif(
    not hasattr(signal, "SIGALRM"), reason="SIGALRM is Unix-only"
)


def test_raises_timeout_error_when_blocking_past_deadline():
    with pytest.raises(TimeoutError):
        with signal_timeout(0.2, "slow poll"):
            time.sleep(5)


def test_no_timeout_when_blocking_finishes_in_time():
    started = time.monotonic()
    with signal_timeout(2.0, "fast poll"):
        time.sleep(0.05)
    assert time.monotonic() - started < 2.0


def test_timeout_message_names_the_operation():
    try:
        with signal_timeout(0.2, "network fetch"):
            time.sleep(5)
    except TimeoutError as exc:
        message = str(exc)
        assert "network fetch" in message
        assert "0.2" in message
    else:
        pytest.fail("expected TimeoutError")


def test_context_manager_restores_previous_handler():
    previous = signal.getsignal(signal.SIGALRM)
    with signal_timeout(0.5, "probe"):
        assert signal.getsignal(signal.SIGALRM) is not previous
    assert signal.getsignal(signal.SIGALRM) is previous


def test_context_manager_restores_pending_alarm():
    """A pending outer alarm (e.g. the autouse 30 s timeout) must survive."""
    signal.alarm(10)
    try:
        with signal_timeout(0.2, "inner"):
            pass
        remaining = signal.getitimer(signal.ITIMER_REAL)[0]
        # The outer 10 s alarm is still ticking (a few seconds may have
        # elapsed under xdist load, so allow generous slack).
        assert 0 < remaining <= 10
    finally:
        signal.alarm(0)


def test_nested_timeouts_inner_fires_first():
    with pytest.raises(TimeoutError):
        with signal_timeout(2.0, "outer"):
            with signal_timeout(0.2, "inner"):
                time.sleep(5)


def test_exception_inside_block_propagates_and_cleans_up():
    previous = signal.getsignal(signal.SIGALRM)
    with pytest.raises(ValueError):
        with signal_timeout(1.0, "boom"):
            raise ValueError("inner failure")
    # Guard fully unwound: handler restored; the outer autouse 30 s timer
    # is ticking again (nothing left over from the inner guard).
    assert signal.getsignal(signal.SIGALRM) is previous
    remaining = signal.getitimer(signal.ITIMER_REAL)[0]
    assert 0 < remaining <= 30
