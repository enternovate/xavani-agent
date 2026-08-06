# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""A04: turn finalizer + retry-state unit tests."""

from __future__ import annotations

from agent.turn_finalizer import (
    EXIT_COMPLETED,
    EXIT_ERROR,
    EXIT_INTERRUPTED,
    EXIT_MAX_ITERATIONS,
    EXIT_TOOL_LIMIT,
    TurnOutcome,
    finalize_turn,
)
from agent.turn_retry_state import TurnRetryState


def test_completed_turn_never_retries():
    outcome = finalize_turn(EXIT_COMPLETED)
    assert outcome.exit_reason == EXIT_COMPLETED
    assert outcome.should_retry() is False
    assert outcome.next_retry_delay() == 0.0


def test_control_exits_never_retry():
    for reason in (EXIT_TOOL_LIMIT, EXIT_MAX_ITERATIONS, EXIT_INTERRUPTED):
        assert finalize_turn(reason).should_retry() is False


def test_error_retries_until_max():
    outcome = finalize_turn(EXIT_ERROR, error="boom", max_retries=2)
    assert outcome.should_retry() is True
    assert outcome.retry.attempt == 1
    assert outcome.error == "boom"
    # Second failure exhausts the budget.
    outcome = finalize_turn(EXIT_ERROR, error="boom again", retry_state=outcome.retry)
    assert outcome.retry.attempt == 2
    assert outcome.should_retry() is False
    assert outcome.next_retry_delay() == 0.0


def test_backoff_grows_and_caps():
    state = TurnRetryState()
    state.record_failure()
    assert state.backoff_seconds() == 1.0
    state.record_failure()
    assert state.backoff_seconds() == 2.0
    state.record_failure()
    assert state.backoff_seconds() == 4.0


def test_retry_state_reset_clears_failures():
    state = TurnRetryState(max_retries=1)
    state.record_failure("bad")
    assert state.should_retry() is False
    state.reset()
    assert state.should_retry() is True
    assert state.last_error == ""


def test_shared_retry_state_carries_across_finalize_calls():
    state = TurnRetryState(max_retries=1)
    first = finalize_turn(EXIT_ERROR, error="e1", retry_state=state)
    second = finalize_turn(EXIT_ERROR, error="e2", retry_state=state)
    assert first.retry is second.retry
    assert state.attempt == 2
    assert isinstance(second, TurnOutcome)
