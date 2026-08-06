# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""A04: turn finalizer (extracted for testability).

Decides how a turn ends.  The conversation-loop tail has many exit
paths; each one reduces to an exit reason plus an optional failure.
``finalize_turn`` maps that pair to a decision: finish, or retry with
backoff.  The retry bookkeeping lives in :mod:`agent.turn_retry_state`.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent.turn_retry_state import DEFAULT_MAX_RETRIES, TurnRetryState

# Exit reasons shared by every loop tail path.
EXIT_COMPLETED = "completed"
EXIT_TOOL_LIMIT = "tool_limit"
EXIT_MAX_ITERATIONS = "max_iterations"
EXIT_INTERRUPTED = "interrupted"
EXIT_REDIRECTED = "redirected"
EXIT_ERROR = "error"

# Exit reasons that never retry.
_NON_RETRYABLE = frozenset(
    {EXIT_COMPLETED, EXIT_TOOL_LIMIT, EXIT_MAX_ITERATIONS, EXIT_INTERRUPTED, EXIT_REDIRECTED}
)


@dataclass
class TurnOutcome:
    """Result of finalizing one turn."""

    exit_reason: str
    retry: TurnRetryState
    error: str = ""

    def should_retry(self) -> bool:
        """True when the turn should run again after a failure."""
        if self.exit_reason in _NON_RETRYABLE:
            return False
        return self.retry.should_retry()

    def next_retry_delay(self) -> float:
        """Seconds to wait before the next attempt (0 when no retry)."""
        if not self.should_retry():
            return 0.0
        return self.retry.backoff_seconds()


def finalize_turn(
    exit_reason: str,
    error: str = "",
    retry_state: TurnRetryState | None = None,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> TurnOutcome:
    """Record the turn's end and produce a retry decision.

    ``exit_reason`` is one of the ``EXIT_*`` constants.  Only failures
    (``EXIT_ERROR``) consume a retry attempt; every other reason ends
    the turn.
    """
    retry = retry_state if retry_state is not None else TurnRetryState(max_retries=max_retries)
    if exit_reason == EXIT_ERROR:
        retry.record_failure(error)
    return TurnOutcome(exit_reason=exit_reason, retry=retry, error=error)
