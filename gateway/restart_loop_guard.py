"""Restart-loop circuit breaker (A09).

A gateway that crashes in a tight loop (bad config, poisoned state, an
external supervisor with a bad trigger) respawns forever, burning CPU and
log volume while masking the real error. This module records each boot in
a rolling window persisted across processes — each boot is a fresh
process, so in-memory state is useless — and reports the loop as
"tripped" once too many boots happen inside a short window.

When tripped, the caller stops starting the gateway and surfaces the
error so a human intervenes, instead of crash-looping silently.

State lives in ``<XAVANI_HOME>/gateway/restart_loop.json`` so it is
profile-scoped and survives process death. It is intentionally tiny and
best-effort: any read/write failure fails OPEN (no false trip) because a
broken breaker must never wedge a healthy gateway.
"""

from __future__ import annotations

import json
import logging
import time
from typing import List

from xavani_constants import get_xavani_home

logger = logging.getLogger(__name__)

# Defaults: 5+ boots in 5 minutes trips the breaker. A legitimate operator
# restart (or two) never trips it; a ~10s crash loop does within a minute.
DEFAULT_MAX_RESTARTS = 5
DEFAULT_WINDOW_SECONDS = 300


def _state_path():
    return get_xavani_home() / "gateway" / "restart_loop.json"


def _load_boots() -> List[float]:
    try:
        raw = _state_path().read_text(encoding="utf-8")
        data = json.loads(raw)
        boots = data.get("boots", [])
        return [float(t) for t in boots if isinstance(t, (int, float))]
    except (OSError, ValueError, TypeError):
        return []


def _save_boots(boots: List[float]) -> None:
    try:
        path = _state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"boots": boots}), encoding="utf-8")
    except OSError:
        pass


def record_boot() -> None:
    """Record this boot in the rolling window (called once at startup)."""
    now = time.time()
    boots = _load_boots()
    cutoff = now - DEFAULT_WINDOW_SECONDS
    boots = [b for b in boots if b >= cutoff]
    boots.append(now)
    _save_boots(boots)


def restart_loop_tripped() -> bool:
    """True when too many boots happened inside the window.

    Fails open: any state error returns False so a broken breaker never
    blocks a healthy gateway start.
    """
    now = time.time()
    cutoff = now - DEFAULT_WINDOW_SECONDS
    boots = [b for b in _load_boots() if b >= cutoff]
    return len(boots) >= DEFAULT_MAX_RESTARTS


def reset_breaker() -> None:
    """Clear the boot window (operator reset; also used in tests)."""
    _save_boots([])


def restart_loop_report() -> str:
    """Human-readable summary of the current boot window."""
    now = time.time()
    cutoff = now - DEFAULT_WINDOW_SECONDS
    boots = sorted(b for b in _load_boots() if b >= cutoff)
    return (
        f"{len(boots)}/{DEFAULT_MAX_RESTARTS} gateway boots in the last "
        f"{DEFAULT_WINDOW_SECONDS}s window "
        f"(limit {DEFAULT_MAX_RESTARTS} within {DEFAULT_WINDOW_SECONDS}s)"
    )


__all__ = [
    "record_boot",
    "restart_loop_tripped",
    "reset_breaker",
    "restart_loop_report",
    "DEFAULT_MAX_RESTARTS",
    "DEFAULT_WINDOW_SECONDS",
]
