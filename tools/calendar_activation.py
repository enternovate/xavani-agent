# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""B15: calendar activation.

Schedules tasks to activate at specific dates/times. The scheduler is a
deterministic queue: tasks register with an ISO timestamp, the checker
reports which tasks are due, and the runner marks them activated.
Supports recurring tasks (daily / weekly / monthly) and one-shot tasks.

The scheduler NEVER runs the task itself — it reports due tasks so the
caller (cron gateway, CLI loop) can execute them. This keeps calendar
activation testable and side-effect free.

Usage::

    from tools.calendar_activation import CalendarScheduler

    scheduler = CalendarScheduler()
    scheduler.schedule("daily-report", "2026-08-04T09:00:00", repeat="daily")
    due = scheduler.due(now="2026-08-05T09:00:00")
    scheduler.mark_activated("daily-report", "2026-08-05T09:00:00")
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

REPEATS = ("once", "daily", "weekly", "monthly")

_ISO_FORMATS = ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d")


def _parse_iso(text: str) -> Optional[datetime]:
    text = text.strip()
    for fmt in _ISO_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _next_occurrence(when: datetime, repeat: str) -> datetime:
    """Next activation time for a recurring schedule."""
    if repeat == "daily":
        return when + timedelta(days=1)
    if repeat == "weekly":
        return when + timedelta(weeks=1)
    if repeat == "monthly":
        # Advance month with day clamping.
        month = when.month + 1
        year = when.year
        if month > 12:
            month = 1
            year += 1
        try:
            return when.replace(year=year, month=month)
        except ValueError:
            return when.replace(year=year, month=month, day=28)
    return when  # once — no next occurrence


class CalendarScheduler:
    """Deterministic calendar task scheduler (thread-safe)."""

    def __init__(self, home: Optional[Path] = None):
        self._home = home if home is not None else Path(
            os.environ.get("XAVANI_HOME", "~/.xavani")
        ).expanduser()
        self._path = self._home / "data" / "calendar_schedule.json"
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        try:
            if self._path.exists():
                return json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("calendar load failed: %s", exc)
        return {"tasks": {}}  # task_id -> schedule record

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(self._data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("calendar save failed: %s", exc)

    def schedule(
        self, task_id: str, when: str, *, repeat: str = "once", payload: Any = None
    ) -> bool:
        """Register a task for activation. True when accepted."""
        if repeat not in REPEATS:
            return False
        when_dt = _parse_iso(when)
        if when_dt is None:
            return False
        with self._lock:
            self._data["tasks"][task_id] = {
                "task_id": task_id,
                "next": when_dt.isoformat(timespec="seconds"),
                "repeat": repeat,
                "payload": payload,
                "activated_count": 0,
            }
            self._save()
            return True

    def due(self, now: str | None = None) -> List[Dict[str, Any]]:
        """Tasks due at or before `now` (ISO), in schedule order."""
        now_dt = _parse_iso(now) if now else datetime.now()
        if now_dt is None:
            return []
        due_tasks: List[Dict[str, Any]] = []
        with self._lock:
            for record in self._data["tasks"].values():
                next_dt = _parse_iso(record["next"])
                if next_dt is not None and next_dt <= now_dt:
                    due_tasks.append(dict(record))
        return sorted(due_tasks, key=lambda r: r["next"])

    def mark_activated(self, task_id: str, now: str | None = None) -> bool:
        """Advance a task to its next occurrence. False when unknown."""
        now_dt = _parse_iso(now) if now else datetime.now()
        with self._lock:
            record = self._data["tasks"].get(task_id)
            if record is None:
                return False
            record["activated_count"] = int(record.get("activated_count", 0)) + 1
            if record["repeat"] == "once":
                self._data["tasks"].pop(task_id, None)
            else:
                next_dt = _parse_iso(record["next"])
                if next_dt is None:
                    next_dt = now_dt
                record["next"] = _next_occurrence(next_dt, record["repeat"]).isoformat(
                    timespec="seconds"
                )
            self._save()
            return True

    def cancel(self, task_id: str) -> bool:
        with self._lock:
            if task_id not in self._data["tasks"]:
                return False
            self._data["tasks"].pop(task_id, None)
            self._save()
            return True

    def tasks(self) -> Dict[str, Any]:
        with self._lock:
            return json.loads(json.dumps(self._data["tasks"]))

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return json.loads(json.dumps(self._data))
