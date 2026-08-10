"""No-op loop guard for hashline apply (ported from omp's noop-loop-guard.ts).

A hashline patch can apply cleanly yet change nothing when the body rows are
already byte-identical to the targeted lines.  Some models ignore the soft
hint and keep re-issuing the same bytes; omp captured a case with 182 repeats
in 205 calls.  This module tracks *consecutive byte-identical edit payloads*
per canonical path within one engine/session and escalates: soft warning on
the first two, a hard :class:`~tools.hashline.apply.ApplyError` on the third
(omp's ``NOOP_HARD_LIMIT = 3``).

Escalation choice (documented, matches omp): the soft hint fires once or
twice so the model gets a chance to recover, but a tight bound is what
actually breaks loops in practice — the third identical payload is a hard
error the agent loop must treat as a tool *failure*.

* Counters are keyed by payload, not by file content: re-issuing the same
  bytes after being warned is what we break, while a *different* payload
  (even a failing one) is model progress and restarts the count at 1.
* A successful (non-noop) commit for a path resets its counter (see
  ``NoopGuard.reset``).
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

__all__ = ["NoopGuard", "NOOP_HARD_LIMIT"]


#: After this many consecutive byte-identical no-op payloads on one path the
#: guard escalates from soft warning to a hard ApplyError (omp's limit).
NOOP_HARD_LIMIT = 3


class NoopGuard:
    """Per-path counter of consecutive byte-identical no-op edit payloads.

    ``record`` returns ``(count, escalate)``: ``count`` is the consecutive
    run length for this payload on this path (1 on first sight or after any
    different payload), and ``escalate`` is True once ``count >=
    NOOP_HARD_LIMIT`` — the caller must then raise a hard error.
    """

    def __init__(self) -> None:
        # path -> (payload, consecutive count) of the most recent no-op.
        self._entries: Dict[str, Tuple[str, int]] = {}

    def record(self, path: str, payload: str) -> Tuple[int, bool]:
        """Record a byte-identical no-op payload for ``path``.

        Returns ``(count, escalate)``; ``escalate`` is True once the same
        payload has no-op'd ``NOOP_HARD_LIMIT`` times in a row.
        """
        prev = self._entries.get(path)
        if prev is not None and prev[0] == payload:
            count = prev[1] + 1
        else:
            count = 1  # different payload = progress; restart the run
        self._entries[path] = (payload, count)
        return count, count >= NOOP_HARD_LIMIT

    def reset(self, path: str) -> None:
        """Clear the counter for ``path`` after a successful (non-noop) commit."""
        self._entries.pop(path, None)

    def count(self, path: str) -> int:
        """Current consecutive count for ``path`` (0 when untracked)."""
        prev = self._entries.get(path)
        return prev[1] if prev is not None else 0

    def warning(self, path: str, count: int) -> str:
        """Soft-hint warning text for a no-op at run length ``count``."""
        if count >= 2:
            return (
                f"[{path}]: no-op detected (repeated {count}x) — the same "
                "edit produced no change again; re-read the file before "
                "issuing another edit"
            )
        return (
            f"[{path}]: no-op — the edit produced no change; fix the "
            "PUT/CUT hunks, re-read the file, or drop the section"
        )

    def hard_error(self, path: str, count: int) -> str:
        """Hard-error text once the identical no-op run hits the limit."""
        return (
            f"[{path}]: no-op detected (repeated {count}x) — the identical "
            "edit has not changed the file and the loop guard tripped; stop "
            "and re-read the file before issuing another edit"
        )

    def __len__(self) -> int:
        return len(self._entries)
