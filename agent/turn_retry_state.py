# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""A04: per-turn retry state (extracted for testability).

Small state holder for the conversation-loop tail.  The loop's exit
paths all share the same retry bookkeeping: how many times a turn has
failed, whether another attempt is allowed, and how long to wait before
the next attempt.  Keeping it here makes that policy unit-testable
without driving the 4k-line loop.
"""

from __future__ import annotations

from dataclasses import dataclass

# Cap exponential backoff at 30 seconds.
_MAX_BACKOFF_SECONDS = 30.0
# Default retries before a turn is abandoned.
DEFAULT_MAX_RETRIES = 2


@dataclass
class TurnRetryState:
    """Retry bookkeeping for one turn.

    ``attempt`` counts failures recorded so far.  ``should_retry`` is
    True while attempts remain below ``max_retries``.
    """

    max_retries: int = DEFAULT_MAX_RETRIES
    attempt: int = 0
    last_error: str = ""

    def should_retry(self) -> bool:
        """True when another attempt is allowed."""
        return self.attempt < self.max_retries

    def record_failure(self, error: str = "") -> None:
        """Count one failure and remember its error message."""
        self.attempt += 1
        if error:
            self.last_error = error

    def backoff_seconds(self) -> float:
        """Exponential backoff for the next attempt, capped at 30s."""
        if self.attempt <= 0:
            return 0.0
        return min(2.0 ** (self.attempt - 1), _MAX_BACKOFF_SECONDS)

    def reset(self) -> None:
        """Clear failure count and error (fresh turn)."""
        self.attempt = 0
        self.last_error = ""
