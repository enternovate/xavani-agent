# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""B03: active learning loop.

The system improves from its own feedback: a task that fails produces a
skill suggestion; the suggestion gets validated; a validated suggestion
merges into the skill library. The loop tracks WHAT failed and WHY, so
learning is evidence-driven, not vibes.

State is persisted per XAVANI_HOME so learning survives restarts.

Usage::

    from tools.active_learning import ActiveLearningLoop

    loop = ActiveLearningLoop()
    loop.record_failure(task_type="code-review", error="missed bug")
    loop.record_failure(task_type="code-review", error="missed bug")
    suggestion = loop.suggest_skill("code-review")
    loop.validate_suggestion(suggestion_id, passed=True)
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

# A task type becomes a skill-extraction candidate after this many
# recorded failures.
FAILURE_THRESHOLD = 3


class ActiveLearningLoop:
    """Failure tracker + skill suggestion loop (thread-safe)."""

    def __init__(self, home: Optional[Path] = None):
        self._home = home if home is not None else Path(
            os.environ.get("XAVANI_HOME", "~/.xavani")
        ).expanduser()
        self._path = self._home / "data" / "active_learning.json"
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        try:
            if self._path.exists():
                return json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("active learning load failed: %s", exc)
        return {
            "failures": {},      # task_type -> [failure records]
            "suggestions": {},   # suggestion_id -> suggestion record
        }

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(self._data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("active learning save failed: %s", exc)

    # ── failure tracking ────────────────────────────────────────────

    def record_failure(self, task_type: str, error: str = "") -> int:
        """Record one failed task. Returns the failure count for its type."""
        task_type = task_type or "unknown"
        with self._lock:
            failures = self._data["failures"].setdefault(task_type, [])
            failures.append(
                {"ts": time.time(), "error": error, "suggested": False}
            )
            self._save()
            return len(failures)

    def failure_count(self, task_type: str) -> int:
        with self._lock:
            return len(self._data["failures"].get(task_type, []))

    def failure_types(self) -> List[str]:
        with self._lock:
            return sorted(self._data["failures"].keys())

    # ── suggestion cycle ────────────────────────────────────────────

    def suggest_skill(self, task_type: str) -> Optional[Dict[str, Any]]:
        """Create a skill suggestion once the failure threshold is met.

        Returns the suggestion record, or None when the threshold is not
        met or a suggestion already exists for this task type.
        """
        with self._lock:
            failures = self._data["failures"].get(task_type, [])
            if len(failures) < FAILURE_THRESHOLD:
                return None
            for record in failures:
                if record.get("suggested"):
                    return None
            suggestion_id = f"{task_type}-{int(time.time())}"
            self._data["suggestions"][suggestion_id] = {
                "id": suggestion_id,
                "task_type": task_type,
                "failure_count": len(failures),
                "status": "suggested",
                "created_at": time.time(),
                "errors": [f.get("error", "") for f in failures[-5:]],
            }
            for record in failures:
                record["suggested"] = True
            self._save()
            return self._data["suggestions"][suggestion_id]

    def validate_suggestion(self, suggestion_id: str, passed: bool) -> bool:
        """Mark a suggestion validated (passed) or rejected (failed)."""
        with self._lock:
            suggestion = self._data["suggestions"].get(suggestion_id)
            if suggestion is None:
                return False
            suggestion["status"] = "merged" if passed else "rejected"
            suggestion["validated_at"] = time.time()
            self._save()
            return True

    def pending_suggestions(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                s for s in self._data["suggestions"].values()
                if s.get("status") == "suggested"
            ]

    def merged_suggestions(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                s for s in self._data["suggestions"].values()
                if s.get("status") == "merged"
            ]

    def snapshot(self) -> Dict[str, Any]:
        """Full state for dashboards and tests."""
        with self._lock:
            return json.loads(json.dumps(self._data))


def threshold() -> int:
    """Public accessor for the failure threshold."""
    return FAILURE_THRESHOLD
