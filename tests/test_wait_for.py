# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the shared deadline-based poller (anti-flake helper).

The `wait_for_state` fixture in tests/conftest.py is the canonical way to
wait on a condition in timing-fragile tests. It replaces fixed sleeps and
fixed iteration caps that flake under pytest-xdist scheduler jitter.
"""

import time


def test_wait_for_state_returns_true_when_predicate_satisfied(wait_for_state):
    # The condition is False at the start, then becomes True.
    ready = [False]

    def predicate():
        return ready[0]

    assert wait_for_state(predicate, timeout=0.2, interval=0.01) is False
    ready[0] = True
    assert wait_for_state(predicate, timeout=0.2, interval=0.01) is True


def test_wait_for_state_times_out_without_satisfying(wait_for_state):
    # The predicate stays False for the whole window.
    started = time.monotonic()
    result = wait_for_state(lambda: False, timeout=0.2, interval=0.02)
    assert result is False
    # It must not wait much longer than the deadline.
    assert time.monotonic() - started < 5
