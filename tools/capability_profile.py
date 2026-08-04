# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""B07: model capability self-assessment.

Tracks each model's measured success per task type (from task outcome
signals) and produces a capability profile: what is this model
actually good at, based on evidence? The profile feeds the B05 model
router so routing decisions use measured capability, not marketing.

Only measured outcomes count. A model with no evidence has no profile.

Usage::

    from tools.capability_profile import CapabilityTracker

    tracker = CapabilityTracker()
    tracker.record_outcome(model="claude-opus", task_type="code-review", success=True)
    profile = tracker.profile("claude-opus")
    best = tracker.best_for("code-review")
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

# Minimum outcomes before a (model, task) capability is reported.
MIN_OUTCOMES = 2


class CapabilityTracker:
    """Per-model, per-task success tracker (thread-safe)."""

    def __init__(self, home: Optional[Path] = None):
        self._home = home if home is not None else Path(
            os.environ.get("XAVANI_HOME", "~/.xavani")
        ).expanduser()
        self._path = self._home / "data" / "capability_profiles.json"
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        try:
            if self._path.exists():
                return json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("capability load failed: %s", exc)
        return {"models": {}}  # model -> {task_type -> {success, total}}

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(self._data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("capability save failed: %s", exc)

    def record_outcome(self, model: str, task_type: str, success: bool) -> None:
        """Record one task outcome for a model."""
        model = model or "unknown"
        task_type = task_type or "unknown"
        with self._lock:
            model_entry = self._data["models"].setdefault(model, {})
            task_entry = model_entry.setdefault(task_type, {"success": 0, "total": 0})
            task_entry["total"] = int(task_entry.get("total", 0)) + 1
            if success:
                task_entry["success"] = int(task_entry.get("success", 0)) + 1
            self._save()

    def task_stats(self, model: str, task_type: str) -> Dict[str, Any]:
        with self._lock:
            entry = (
                self._data["models"]
                .get(model, {})
                .get(task_type)
            )
            if entry is None:
                return {"success": 0, "total": 0, "success_rate": None}
            success = int(entry.get("success", 0))
            total = int(entry.get("total", 0))
            return {
                "success": success,
                "total": total,
                "success_rate": success / total if total else None,
            }

    def profile(self, model: str) -> Dict[str, Any]:
        """Capability profile: per-task rates + ranked strengths."""
        with self._lock:
            model_entry = self._data["models"].get(model, {})
            tasks: Dict[str, Dict[str, Any]] = {}
            for task_type, entry in model_entry.items():
                success = int(entry.get("success", 0))
                total = int(entry.get("total", 0))
                if total < MIN_OUTCOMES:
                    continue
                tasks[task_type] = {
                    "success_rate": success / total,
                    "total": total,
                }
            strengths = sorted(
                tasks.items(), key=lambda kv: (-kv[1]["success_rate"], -kv[1]["total"])
            )
            return {
                "model": model,
                "tasks": tasks,
                "strengths": [task_type for task_type, _ in strengths],
                "evidence_total": sum(
                    int(e.get("total", 0)) for e in model_entry.values()
                ),
            }

    def best_for(self, task_type: str, min_total: int = MIN_OUTCOMES) -> Optional[str]:
        """Model with the highest measured success rate for a task type."""
        with self._lock:
            best_model: Optional[str] = None
            best_rate = -1.0
            for model, model_entry in self._data["models"].items():
                entry = model_entry.get(task_type)
                if entry is None:
                    continue
                total = int(entry.get("total", 0))
                if total < min_total:
                    continue
                rate = int(entry.get("success", 0)) / total
                if rate > best_rate:
                    best_rate = rate
                    best_model = model
            return best_model

    def models(self) -> List[str]:
        with self._lock:
            return sorted(self._data["models"].keys())

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return json.loads(json.dumps(self._data))
