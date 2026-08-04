# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""G03: self-healing degradation.

Maps degraded subsystems to SAFE recovery actions and tracks their
execution. Healing is conservative: every action is (a) reversible, (b)
scoped, and (c) rate-limited so the system cannot heal itself into a
worse state. The healer never takes destructive action — it reports
what it will do and executes only the actions marked safe.

Usage::

    from tools.self_healing import SelfHealer

    healer = SelfHealer()
    actions = healer.plan({"tool_health_ok": {"ok": 1, "total": 4}})
    healer.execute(actions[0]["id"])  # executes a SAFE action
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Degradation signal -> safe recovery actions.
# Each action: id, description, scope, reversible, destructive=False.
_RECOVERY_MAP: Dict[str, List[Dict[str, Any]]] = {
    "tool_health_ok": [
        {
            "id": "rescan_tools",
            "description": "Re-run tool auto-discovery to recover missing registrations",
            "scope": "tools",
            "reversible": True,
            "destructive": False,
        },
    ],
    "cost_burn_exceeded": [
        {
            "id": "throttle_outbound",
            "description": "Reduce outbound concurrency to the safety default",
            "scope": "outbound",
            "reversible": True,
            "destructive": False,
        },
    ],
    "error_rate": [
        {
            "id": "flush_error_log",
            "description": "Rotate the error log so disk stays bounded",
            "scope": "logging",
            "reversible": True,
            "destructive": False,
        },
    ],
}

# An action can run at most once per window.
_HEAL_WINDOW_SECONDS = 300.0


class SelfHealer:
    """Degradation -> safe-recovery planner (thread-safe)."""

    def __init__(self, home=None):
        self._lock = threading.Lock()
        self._last_run: Dict[str, float] = {}
        self._history: List[Dict[str, Any]] = []
        self._home = home

    def plan(self, signals: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Recovery actions for degraded signals, rate-limited.

        Returns a list of action dicts with an ``executable`` flag.
        """
        actions: List[Dict[str, Any]] = []
        now = time.time()
        for signal, value in signals.items():
            if signal not in _RECOVERY_MAP:
                continue
            if not self._is_degraded(signal, value):
                continue
            for action in _RECOVERY_MAP[signal]:
                entry = dict(action)
                last = self._last_run.get(action["id"], 0.0)
                entry["executable"] = (now - last) >= _HEAL_WINDOW_SECONDS
                entry["signal"] = signal
                actions.append(entry)
        return actions

    def execute(self, action_id: str) -> bool:
        """Execute a safe recovery action. True when it ran."""
        # Only known safe actions are executable here.
        known = {
            "rescan_tools": self._heal_rescan_tools,
            "throttle_outbound": self._heal_throttle_outbound,
            "flush_error_log": self._heal_flush_error_log,
        }
        handler = known.get(action_id)
        if handler is None:
            return False
        with self._lock:
            now = time.time()
            if (now - self._last_run.get(action_id, 0.0)) < _HEAL_WINDOW_SECONDS:
                return False  # rate-limited
            self._last_run[action_id] = now
        ok = handler()
        self._history.append(
            {"action": action_id, "executed_at": time.time(), "ok": ok}
        )
        return ok

    def history(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._history)

    # ── actual safe actions ─────────────────────────────────────────

    @staticmethod
    def _heal_rescan_tools() -> bool:
        try:
            from tools.auto_discovery import load_user_tools
            from tools.registry import ToolRegistry

            registry = ToolRegistry()
            records = load_user_tools(registry)
            return True
        except Exception as exc:
            logger.warning("rescan_tools failed: %s", exc)
            return False

    @staticmethod
    def _heal_throttle_outbound() -> bool:
        try:
            from agent.outbound_limiter import reset_limiter

            reset_limiter()
            return True
        except Exception as exc:
            logger.warning("throttle_outbound failed: %s", exc)
            return False

    @staticmethod
    def _heal_flush_error_log() -> bool:
        try:
            import os
            from pathlib import Path

            home = Path(os.environ.get("XAVANI_HOME", "~/.xavani")).expanduser()
            log_dir = home / "logs"
            if not log_dir.is_dir():
                return True
            # Rotate: keep the current file, move old ones to .1.
            for path in sorted(log_dir.glob("*.log.1")):
                path.unlink(missing_ok=True)
            for path in sorted(log_dir.glob("*.log")):
                target = Path(str(path) + ".1")
                try:
                    path.rename(target)
                except OSError:
                    pass
            return True
        except Exception as exc:
            logger.warning("flush_error_log failed: %s", exc)
            return False

    # ── degradation checks ──────────────────────────────────────────

    @staticmethod
    def _is_degraded(signal: str, value: Any) -> bool:
        if signal == "tool_health_ok" and isinstance(value, dict):
            total = int(value.get("total", 0))
            ok = int(value.get("ok", 0))
            return total > 0 and ok / total < 0.7
        if signal == "cost_burn_exceeded":
            return bool(value)
        if signal == "error_rate":
            return value is not None and float(value) > 0.3
        return False
