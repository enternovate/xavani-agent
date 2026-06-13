# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Operator daemon — 24/7 service with a heartbeat (v1.0.0 major ③).

Wraps a cycle ``tick`` in an unattended loop with a **heartbeat** file and a
readable **status**, so the operator can run as a launchd/systemd/Docker service.
The user's contract — *"active only when actually working and generating results"*
— is honoured literally: a tick that produces no result records status ``idle``
(cheap, no LLM); a tick that acts records ``working`` and what it produced.

The clock, sleep, and tick are **injected**, so this is unit-tested without real
time or a real loop. Deterministic and zero-LLM here (the tick may use the LLM via
propose; the daemon itself never does). Mirrors ``xavani_operator/continuous.py``.

heartbeat.json fields: ``status`` (starting|idle|working|stopped), ``cycle_count``
(int), ``acted`` (int), ``last_tick`` (epoch float), ``note`` (str).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable


def _xavani_home() -> Path:
    try:
        from xavani_constants import get_xavani_home

        return get_xavani_home()
    except Exception:  # pragma: no cover - fallback only
        import os

        return Path(os.path.expanduser("~/.xavani"))


def heartbeat_path() -> Path:
    return _xavani_home() / "operator" / "daemon" / "heartbeat.json"


def write_heartbeat(
    status: str,
    *,
    cycle_count: int = 0,
    acted: int = 0,
    note: str = "",
    path: str | Path | None = None,
    now: float | None = None,
) -> dict:
    """Atomically write the heartbeat file and return the record."""
    rec = {
        "status": status,
        "cycle_count": cycle_count,
        "acted": acted,
        "last_tick": now if now is not None else time.time(),
        "note": note,
    }
    p = Path(path) if path is not None else heartbeat_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(rec, indent=2), encoding="utf-8")
    tmp.replace(p)
    return rec


def read_status(path: str | Path | None = None) -> dict:
    """Read the heartbeat file ({} if absent/corrupt)."""
    p = Path(path) if path is not None else heartbeat_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def serve(
    tick: Callable[[], dict],
    *,
    interval: float = 60.0,
    max_iters: int | None = None,
    clock: Callable[[], float] = time.time,
    sleep: Callable[[float], Any] = time.sleep,
    stop: Callable[[], bool] | None = None,
    paused: Callable[[], bool] | None = None,
    heartbeat: str | Path | None = None,
) -> dict:
    """Run the daemon loop. Returns a summary.

    Each iteration calls ``tick()`` which returns a dict; ``tick`` is considered to
    have *worked* when its result is truthy and ``result.get("acted")`` is true.
    A heartbeat is written every iteration so external supervisors can see liveness.
    Loops until ``max_iters`` is reached or ``stop()`` returns True. When ``paused()``
    is true (the kill-switch), the cycle is skipped — a ``paused`` heartbeat is written
    and no work runs — until it clears.
    """
    write_heartbeat("starting", path=heartbeat, now=clock())
    iters = 0
    acted = 0
    paused_count = 0
    last_status = "starting"
    while True:
        if max_iters is not None and iters >= max_iters:
            break
        if stop is not None and stop():
            break
        iters += 1
        if paused is not None and paused():
            paused_count += 1
            last_status = "paused"
            write_heartbeat(
                "paused",
                cycle_count=iters,
                acted=acted,
                note="kill-switch engaged — run `xavani operator resume` to continue",
                path=heartbeat,
                now=clock(),
            )
        else:
            result = tick() or {}
            did_act = bool(result.get("acted"))
            if did_act:
                acted += 1
            last_status = "working" if did_act else "idle"
            write_heartbeat(
                last_status,
                cycle_count=iters,
                acted=acted,
                note=str(result.get("note", "")),
                path=heartbeat,
                now=clock(),
            )
        if max_iters is not None and iters >= max_iters:
            break
        if stop is not None and stop():
            break
        sleep(interval)

    summary = {
        "iters": iters,
        "acted": acted,
        "idle": iters - acted - paused_count,
        "paused": paused_count,
        "last_status": last_status,
    }
    write_heartbeat("stopped", cycle_count=iters, acted=acted, note="serve() returned", path=heartbeat, now=clock())
    return summary
