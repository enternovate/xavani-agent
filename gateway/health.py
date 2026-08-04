"""Gateway health + readiness state (A10/E01).

Pure state functions for orchestrators: ``/health`` reports liveness,
``/ready`` reports whether the gateway can take inbound traffic (at least
one messaging platform connected). The gateway registers a live-state
provider at startup; without one, readiness fails open as "not ready"
until platforms connect.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional

_started_at: float = time.time()
_state_provider: Optional[Callable[[], Dict[str, Any]]] = None


def set_state_provider(fn: Optional[Callable[[], Dict[str, Any]]]) -> None:
    """Register the gateway's live-state provider (called per request)."""
    global _state_provider
    _state_provider = fn


def _live_state() -> Dict[str, Any]:
    if _state_provider is not None:
        try:
            state = _state_provider() or {}
            if isinstance(state, dict):
                return state
        except Exception:
            pass
    return {}


def health_status() -> Dict[str, Any]:
    """Liveness payload: the process is up (it answered the request)."""
    state = _live_state()
    return {
        "status": "ok",
        "uptime_seconds": round(time.time() - _started_at, 1),
        "version": state.get("version", ""),
        "platforms_connected": state.get("platforms_connected", 0),
        "platforms": state.get("platforms", []),
        "running": bool(state.get("running", True)),
    }


def readiness_status() -> Dict[str, Any]:
    """Readiness payload: ready only when a messaging platform is connected."""
    state = _live_state()
    connected = int(state.get("platforms_connected", 0))
    ready = connected > 0 and bool(state.get("running", True))
    reason = "ok" if ready else (
        "no messaging platform connected" if connected == 0 else "gateway not running"
    )
    return {
        "ready": ready,
        "reason": reason,
        "platforms_connected": connected,
        "platforms": state.get("platforms", []),
    }


__all__ = [
    "set_state_provider",
    "health_status",
    "readiness_status",
]
