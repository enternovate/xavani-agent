# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""G05: scheduled maintenance.

A maintenance planner that proposes WHEN maintenance tasks should run
(weekly, monthly) and tracks whether they ran. Uses the B15 calendar
scheduler for the schedule and records completion in the maintenance
log. The planner never executes maintenance itself — it reports due
maintenance so the operator or a cron job can run it.

Usage::

    from tools.scheduled_maintenance import MaintenancePlanner

    planner = MaintenancePlanner()
    planner.plan("prune-sessions", repeat="weekly", payload={...})
    due = planner.due(now="2026-08-11T03:00:00")
    planner.complete("prune-sessions", "2026-08-11T03:00:00")
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

REPEATS = ("daily", "weekly", "monthly")


class MaintenancePlanner:
    """Planned maintenance tracker (thread-safe)."""

    def __init__(self, home: Optional[Path] = None):
        self._home = home if home is not None else Path(
            os.environ.get("XAVANI_HOME", "~/.xavani")
        ).expanduser()
        self._path = self._home / "data" / "maintenance.json"
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        try:
            if self._path.exists():
                return json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("maintenance load failed: %s", exc)
        return {"tasks": {}, "history": []}

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(self._data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("maintenance save failed: %s", exc)

    def plan(self, task_id: str, when: str, *, repeat: str, payload: Any = None) -> bool:
        """Plan a maintenance task. True when accepted."""
        if repeat not in REPEATS:
            return False
        try:
            from tools.calendar_activation import _parse_iso

            if _parse_iso(when) is None:
                return False
        except Exception:
            return False
        with self._lock:
            self._data["tasks"][task_id] = {
                "task_id": task_id,
                "next": when,
                "repeat": repeat,
                "payload": payload,
                "last_completed": None,
            }
            self._save()
            return True

    def due(self, now: str | None = None) -> List[Dict[str, Any]]:
        """Maintenance tasks due at or before `now` (ISO)."""
        try:
            from tools.calendar_activation import _parse_iso

            now_dt = _parse_iso(now) if now else None
        except Exception:
            now_dt = None
        due_tasks: List[Dict[str, Any]] = []
        with self._lock:
            for record in self._data["tasks"].values():
                next_dt = None
                try:
                    from tools.calendar_activation import _parse_iso

                    next_dt = _parse_iso(record["next"])
                except Exception:
                    pass
                if next_dt is None:
                    continue
                if now_dt is None or next_dt <= now_dt:
                    due_tasks.append(dict(record))
        return sorted(due_tasks, key=lambda r: r["next"])

    def complete(self, task_id: str, now: str | None = None) -> bool:
        """Mark maintenance complete; advance to the next occurrence."""
        from tools.calendar_activation import _next_occurrence, _parse_iso

        now_dt = _parse_iso(now) if now else None
        with self._lock:
            record = self._data["tasks"].get(task_id)
            if record is None:
                return False
            record["last_completed"] = now or (
                now_dt.isoformat(timespec="seconds") if now_dt else None
            )
            next_dt = _parse_iso(record["next"])
            if next_dt is not None:
                record["next"] = _next_occurrence(
                    next_dt, record["repeat"]
                ).isoformat(timespec="seconds")
            self._data["history"].append(
                {"task_id": task_id, "completed_at": record["last_completed"]}
            )
            self._save()
            return True

    def tasks(self) -> Dict[str, Any]:
        with self._lock:
            return json.loads(json.dumps(self._data["tasks"]))

    def history(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._data["history"])

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return json.loads(json.dumps(self._data))
