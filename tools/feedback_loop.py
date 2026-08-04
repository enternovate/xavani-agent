# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""B13: feedback loop.

Tracks explicit user feedback on responses (thumbs up / down / retry)
per task type and feeds the numbers back into the loop: a task type
with a poor satisfaction trend becomes a learning candidate (see B03
active learning) and surfaces in status dashboards.

Only EXPLICIT feedback counts — the system never infers satisfaction
from silence.

Usage::

    from tools.feedback_loop import FeedbackLoop

    loop = FeedbackLoop()
    loop.record("code-review", "up")
    loop.record("code-review", "down")
    trend = loop.trend("code-review")   # {"up": 1, "down": 1, "satisfaction": 0.5}
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

VALID_SIGNALS = ("up", "down", "retry")
# A task type is "struggling" when satisfaction drops below this.
STRUGGLE_THRESHOLD = 0.4


class FeedbackLoop:
    """Explicit-feedback tracker with per-task-type trends (thread-safe)."""

    def __init__(self, home: Optional[Path] = None):
        self._home = home if home is not None else Path(
            os.environ.get("XAVANI_HOME", "~/.xavani")
        ).expanduser()
        self._path = self._home / "data" / "feedback.json"
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        try:
            if self._path.exists():
                return json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("feedback load failed: %s", exc)
        return {"events": [], "by_task": {}}

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(self._data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("feedback save failed: %s", exc)

    def record(self, task_type: str, signal: str, note: str = "") -> bool:
        """Record one explicit feedback signal. True when accepted."""
        if signal not in VALID_SIGNALS:
            return False
        task_type = task_type or "unknown"
        with self._lock:
            self._data["events"].append(
                {
                    "task_type": task_type,
                    "signal": signal,
                    "note": note,
                    "ts": time.time(),
                }
            )
            by_task = self._data["by_task"].setdefault(task_type, {"up": 0, "down": 0, "retry": 0})
            by_task[signal] = int(by_task.get(signal, 0)) + 1
            self._save()
            return True

    def counts(self, task_type: str) -> Dict[str, int]:
        with self._lock:
            entry = self._data["by_task"].get(task_type)
            return dict(entry) if entry else {"up": 0, "down": 0, "retry": 0}

    def satisfaction(self, task_type: str) -> Optional[float]:
        """Satisfaction = up / (up + down). None when no decisive votes."""
        counts = self.counts(task_type)
        decisive = counts["up"] + counts["down"]
        if decisive == 0:
            return None
        return counts["up"] / decisive

    def trend(self, task_type: str) -> Dict[str, Any]:
        counts = self.counts(task_type)
        satisfaction = self.satisfaction(task_type)
        return {
            "task_type": task_type,
            **counts,
            "satisfaction": satisfaction,
            "struggling": (
                satisfaction is not None and satisfaction < STRUGGLE_THRESHOLD
            ),
        }

    def struggling_tasks(self) -> List[str]:
        with self._lock:
            struggling = []
            for task_type, counts in self._data["by_task"].items():
                decisive = counts.get("up", 0) + counts.get("down", 0)
                if decisive == 0:
                    continue
                satisfaction = counts.get("up", 0) / decisive
                if satisfaction < STRUGGLE_THRESHOLD:
                    struggling.append(task_type)
            return sorted(struggling)

    def event_count(self) -> int:
        with self._lock:
            return len(self._data["events"])

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return json.loads(json.dumps(self._data))
