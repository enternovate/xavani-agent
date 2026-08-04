# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""B09: metacognition — confidence calibration tracking.

Tracks the agent's own confidence estimates against actual outcomes
and measures calibration: "when I said 90% confident, was I right 90%
of the time?" Overconfident and underconfident regions surface so the
system can correct its own judgment.

Only EXPLICIT confidence estimates are tracked — the system never
invents a confidence after the fact.

Usage::

    from tools.metacognition import CalibrationTracker

    tracker = CalibrationTracker()
    tracker.record_estimate(task_id="t1", confidence=0.9)
    tracker.record_outcome(task_id="t1", success=True)
    report = tracker.calibration_report()
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

# Confidence buckets for the calibration report (edges inclusive).
_BUCKETS = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01)]


class CalibrationTracker:
    """Confidence-vs-outcome tracker (thread-safe)."""

    def __init__(self, home: Optional[Path] = None):
        self._home = home if home is not None else Path(
            os.environ.get("XAVANI_HOME", "~/.xavani")
        ).expanduser()
        self._path = self._home / "data" / "metacognition.json"
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        try:
            if self._path.exists():
                return json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("metacognition load failed: %s", exc)
        return {"pending": {}, "resolved": []}  # task_id -> estimate

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(self._data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("metacognition save failed: %s", exc)

    def record_estimate(self, task_id: str, confidence: float) -> bool:
        """Record an explicit confidence estimate (0.0..1.0)."""
        if not 0.0 <= confidence <= 1.0:
            return False
        with self._lock:
            self._data["pending"][task_id] = {
                "confidence": confidence,
                "ts": time.time(),
            }
            self._save()
            return True

    def record_outcome(self, task_id: str, success: bool) -> bool:
        """Resolve a pending estimate with the actual outcome."""
        with self._lock:
            estimate = self._data["pending"].pop(task_id, None)
            if estimate is None:
                return False
            self._data["resolved"].append(
                {
                    "task_id": task_id,
                    "confidence": estimate["confidence"],
                    "success": bool(success),
                    "ts": time.time(),
                }
            )
            self._save()
            return True

    def resolved_count(self) -> int:
        with self._lock:
            return len(self._data["resolved"])

    def pending_count(self) -> int:
        with self._lock:
            return len(self._data["pending"])

    def calibration_report(self, min_samples: int = 3) -> Dict[str, Any]:
        """Bucketed calibration report.

        Each bucket: confidence range, samples, actual success rate,
        and the gap (success_rate - mid_confidence). Positive gap =
        underconfident; negative gap = overconfident.
        """
        with self._lock:
            resolved = list(self._data["resolved"])
        buckets: List[Dict[str, Any]] = []
        for low, high in _BUCKETS:
            samples = [
                r for r in resolved
                if low <= r["confidence"] < high
            ]
            if not samples:
                continue
            actual = sum(1 for r in samples if r["success"]) / len(samples)
            mid = (low + high) / 2
            buckets.append(
                {
                    "range": f"{low:.1f}-{min(high, 1.0):.1f}",
                    "samples": len(samples),
                    "actual_success_rate": round(actual, 3),
                    "mid_confidence": round(mid, 3),
                    "gap": round(actual - mid, 3),
                }
            )
        reported = [b for b in buckets if b["samples"] >= min_samples]
        overconfident = [
            b for b in reported if b["gap"] < -0.1
        ]
        underconfident = [
            b for b in reported if b["gap"] > 0.1
        ]
        return {
            "total_resolved": len(resolved),
            "buckets": buckets,
            "reported": reported,
            "overconfident": overconfident,
            "underconfident": underconfident,
            "calibrated": [b for b in reported if -0.1 <= b["gap"] <= 0.1],
        }

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return json.loads(json.dumps(self._data))
