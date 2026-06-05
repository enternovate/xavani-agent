# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Continuous operation (v0.7.0 operator U81/U83/U85/U87).

Turns the single-cycle operator into an unattended service: ``run_continuous``
loops, and on each tick decides whether to run a cycle based on three
**deterministic** gates (R10):

* **quiet hours** — never act during the configured window (``HH:MM-HH:MM``);
* **concurrency lock** — one cycle per repo at a time (TTL'd so a crash frees it);
* **backpressure** — pause new cycles when approvals pile up past a threshold.

The cycle itself (``run_once``) and the clock/sleep are injected, so this is unit
tested without real time or a real loop. No LLM, no network here.
"""

from __future__ import annotations

import re
import time
from datetime import datetime
from typing import Any, Callable

_LOCK_COLLECTION = "locks"
_DEFAULT_MAX_PENDING = 20


def _safe(name: str) -> str:
    # Note: dots are mapped to '_' too, so a repo path of "." never becomes the
    # reserved state key "." / ".." (which the store rejects).
    return re.sub(r"[^A-Za-z0-9_-]", "_", name) or "default"


def _minutes(hhmm: str) -> int:
    h, m = hhmm.strip().split(":")
    return int(h) * 60 + int(m)


def in_quiet_hours(spec: str, now: datetime) -> bool:
    """True if ``now`` falls in the ``HH:MM-HH:MM`` quiet window (overnight aware)."""
    if not spec or "-" not in spec:
        return False
    start_s, end_s = spec.split("-", 1)
    try:
        start, end = _minutes(start_s), _minutes(end_s)
    except (ValueError, IndexError):
        return False
    cur = now.hour * 60 + now.minute
    if start <= end:
        return start <= cur < end
    return cur >= start or cur < end  # wraps past midnight


def acquire_lock(state: Any, key: str, ttl: int = 3600, now: float | None = None) -> bool:
    """Acquire a per-key cycle lock; ``False`` if a fresh lock is held."""
    now = time.time() if now is None else now
    rec = state.get(_LOCK_COLLECTION, _safe(key))
    if rec and (now - rec.get("at", 0)) < ttl:
        return False
    state.put(_LOCK_COLLECTION, _safe(key), {"key": key, "at": now})
    return True


def release_lock(state: Any, key: str) -> None:
    """Release a previously acquired lock."""
    state.delete(_LOCK_COLLECTION, _safe(key))


def backpressure_ok(state: Any, max_pending: int = _DEFAULT_MAX_PENDING) -> bool:
    """True while pending approvals are below ``max_pending`` (else pause new work)."""
    from xavani_operator.approval_queue import ApprovalQueue
    from xavani_operator.types import ProposalStatus

    pending = ApprovalQueue(state).list(ProposalStatus.PENDING)
    return len(pending) < max_pending


def should_run(config: Any, now: datetime | None = None) -> bool:
    """Deterministic 'is it OK to run right now' (quiet-hours gate)."""
    now = now or datetime.now()
    return not in_quiet_hours(config.approval.quiet_hours, now)


def run_continuous(
    config: Any,
    state: Any,
    *,
    run_once: Callable[[], Any],
    iterations: int = 1,
    max_pending: int = _DEFAULT_MAX_PENDING,
    lock_ttl: int = 3600,
    clock: Callable[[], datetime] | None = None,
    sleep_fn: Callable[[float], Any] | None = None,
    interval: float = 60.0,
) -> list[dict]:
    """Run the operator continuously for ``iterations`` ticks; return per-tick outcomes."""
    clock = clock or datetime.now
    sleep_fn = sleep_fn or time.sleep
    lock_key = config.product.repo or "default"
    outcomes: list[dict] = []

    for _ in range(iterations):
        now = clock()
        if in_quiet_hours(config.approval.quiet_hours, now):
            outcomes.append({"status": "quiet"})
            sleep_fn(interval)
            continue
        if not backpressure_ok(state, max_pending):
            outcomes.append({"status": "backpressure"})
            sleep_fn(interval)
            continue
        if not acquire_lock(state, lock_key, ttl=lock_ttl, now=now.timestamp()):
            outcomes.append({"status": "locked"})
            sleep_fn(interval)
            continue
        try:
            result = run_once()
            outcomes.append({"status": "ran", "result": result})
        finally:
            release_lock(state, lock_key)
        sleep_fn(interval)

    return outcomes
