# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Kill-switch — pause/resume the autonomous operator (v1.0.0 ③ / safety).

A single, dead-simple control the user (or a script, or a hook) can flip to stop
the 24/7 daemon from acting — without killing the process or losing its place. It
is a flag *file* so it works across processes and survives restarts: the daemon
checks :func:`is_paused` every tick and idles (writing a ``paused`` heartbeat)
until the flag is cleared.

Pure stdlib, deterministic, zero-LLM (R10).

Flag file: ``<xavani-home>/operator/PAUSED`` — JSON ``{reason: str, ts: float}``.
"""

from __future__ import annotations

import json
import time
from pathlib import Path


def _xavani_home() -> Path:
    try:
        from xavani_constants import get_xavani_home

        return get_xavani_home()
    except Exception:  # pragma: no cover - fallback only
        import os

        return Path(os.path.expanduser("~/.xavani"))


def pause_flag_path() -> Path:
    return _xavani_home() / "operator" / "PAUSED"


def pause(reason: str = "", *, path: str | Path | None = None, now: float | None = None) -> Path:
    """Engage the kill-switch. The daemon stops acting until :func:`resume`."""
    p = Path(path) if path is not None else pause_flag_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps({"reason": reason, "ts": now if now is not None else time.time()}),
        encoding="utf-8",
    )
    return p


def resume(*, path: str | Path | None = None) -> bool:
    """Release the kill-switch. Returns True if it had been engaged."""
    p = Path(path) if path is not None else pause_flag_path()
    if p.exists():
        p.unlink()
        return True
    return False


def is_paused(*, path: str | Path | None = None) -> bool:
    """True if the operator is currently paused."""
    p = Path(path) if path is not None else pause_flag_path()
    return p.exists()


def pause_reason(*, path: str | Path | None = None) -> str | None:
    """The reason recorded when paused, or ``None`` if not paused."""
    p = Path(path) if path is not None else pause_flag_path()
    if not p.exists():
        return None
    try:
        return str(json.loads(p.read_text(encoding="utf-8")).get("reason", ""))
    except (json.JSONDecodeError, OSError):
        return ""
