# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""D08: elevated-privilege re-verification.

Sessions that run for days shouldn't have unlimited privilege. After N
elevated approvals (sudo / dangerous commands), the next one requires
re-verification — the user must confirm the session is still theirs.

Deterministic and thread-safe. Configurable via
XAVANI_PRIVILEGE_RECHECK (default 5 approvals between re-checks).

Usage::

    from tools.privilege_recheck import check_privilege_recheck, mark_privileged_action

    if check_privilege_recheck(session_key):
        # require the user to re-confirm before executing
    mark_privileged_action(session_key)  # after a privileged action ran
"""

from __future__ import annotations

import os
import threading
import time
from typing import Dict, Optional

DEFAULT_RECHECK_EVERY = 5
_WINDOW_SECONDS = 3600.0  # count only approvals in the last hour

_counts: Dict[str, list] = {}  # session_key -> [timestamps of privileged actions]
_counts_lock = threading.Lock()


def configured_recheck_interval() -> int:
    """Resolve the re-check interval from XAVANI_PRIVILEGE_RECHECK."""
    raw = os.environ.get("XAVANI_PRIVILEGE_RECHECK", str(DEFAULT_RECHECK_EVERY))
    try:
        value = int(raw)
        return max(1, value)
    except (TypeError, ValueError):
        return DEFAULT_RECHECK_EVERY


def mark_privileged_action(session_key: str, now: float | None = None) -> None:
    """Record that a privileged action ran in this session."""
    now = now if now is not None else time.time()
    with _counts_lock:
        events = _counts.setdefault(session_key, [])
        events.append(now)
        _prune(events, now)


def _prune(events: list, now: float) -> None:
    cutoff = now - _WINDOW_SECONDS
    while events and events[0] < cutoff:
        events.pop(0)


def check_privilege_recheck(session_key: str, now: float | None = None) -> bool:
    """True when this session must re-verify before its next privileged action.

    True means: the session has hit the re-check threshold within the
    window — require explicit user confirmation. Does NOT auto-reset;
    call :func:`confirm_privilege_recheck` after the user re-verifies.
    """
    interval = configured_recheck_interval()
    now = now if now is not None else time.time()
    with _counts_lock:
        events = _counts.get(session_key, [])
        _prune(events, now)
        return len(events) >= interval


def confirm_privilege_recheck(session_key: str) -> None:
    """Reset the counter after the user re-verified (fresh privilege)."""
    with _counts_lock:
        _counts.pop(session_key, None)


def reset_all() -> None:
    """Wipe all counters. For tests and session teardown."""
    with _counts_lock:
        _counts.clear()


def snapshot(session_key: str) -> Optional[Dict]:
    """Counter state for a session (None when untouched)."""
    with _counts_lock:
        events = _counts.get(session_key)
        if events is None:
            return None
        now = time.time()
        _prune(events, now)
        return {
            "count": len(events),
            "interval": configured_recheck_interval(),
            "recheck_required": len(events) >= configured_recheck_interval(),
        }
