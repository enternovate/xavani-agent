"""Autonomous maintenance window (G03).

Runs when the gateway is idle: session-DB VACUUM, stale-lock garbage
collection, and log rotation. Every step is best-effort and independent —
one failing step never blocks the others, and the whole run never raises.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_LOCK_SUFFIXES = (".lock", ".pid")
_STALE_LOCK_AGE_SECONDS = 3600


def _home() -> Path:
    from xavani_constants import get_xavani_home

    return get_xavani_home()


def _vacuum_session_db() -> Dict[str, Any]:
    """VACUUM the session database."""
    try:
        from xavani_state import SessionDB

        db = SessionDB(_home() / "state.db")
        db.vacuum()
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _gc_stale_locks() -> Dict[str, Any]:
    """Remove lock/pid files older than the stale age."""
    removed = []
    home = _home()
    try:
        for path in home.iterdir():
            if not path.is_file() or not path.name.endswith(_LOCK_SUFFIXES):
                continue
            try:
                age = time.time() - path.stat().st_mtime
                if age > _STALE_LOCK_AGE_SECONDS:
                    path.unlink()
                    removed.append(path.name)
            except OSError:
                continue
    except OSError:
        pass
    return {"ok": True, "removed": removed}


def _rotate_logs() -> Dict[str, Any]:
    """Rotate oversized logs via the gateway memory monitor's check."""
    try:
        from gateway.memory_monitor import _check_disk_and_logs

        _check_disk_and_logs()
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def run_maintenance() -> Dict[str, Any]:
    """Run the full idle-maintenance pass. Never raises."""
    results: Dict[str, Any] = {"ts": time.time()}
    results["vacuum"] = _vacuum_session_db()
    results["stale_locks"] = _gc_stale_locks()
    results["log_rotation"] = _rotate_logs()
    logger.info("Maintenance pass complete: %s", results)
    return results


def gateway_has_active_turns(runner: Any) -> bool:
    """True when the gateway is processing at least one session turn."""
    try:
        running = getattr(runner, "_running_agents", {}) or {}
        return bool(running)
    except Exception:
        return True  # Unknown state: do not interrupt.


__all__ = [
    "run_maintenance",
    "gateway_has_active_turns",
    "_STALE_LOCK_AGE_SECONDS",
]
