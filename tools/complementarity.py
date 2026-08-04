# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""B11: tool complementarity matrix.

Tracks which tools are used TOGETHER in the same task run and records
whether that run succeeded. A complementary pair is a tool combination
that appears in successful runs more often than chance — the matrix
answers "when I reach for tool A, which tool usually finishes the job?"

Usage::

    from tools.complementarity import ComplementarityMatrix

    matrix = ComplementarityMatrix()
    matrix.record_run(tools=["read_file", "patch"], success=True)
    matrix.record_run(tools=["read_file", "patch"], success=True)
    best = matrix.complements("read_file")
"""

from __future__ import annotations

import itertools
import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Minimum co-occurrences before a pair is reported.
MIN_PAIR_OCCURRENCES = 2


class ComplementarityMatrix:
    """Tool co-occurrence tracker with success rates (thread-safe)."""

    def __init__(self, home: Optional[Path] = None):
        self._home = home if home is not None else Path(
            os.environ.get("XAVANI_HOME", "~/.xavani")
        ).expanduser()
        self._path = self._home / "data" / "complementarity.json"
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        try:
            if self._path.exists():
                return json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("complementarity load failed: %s", exc)
        return {"pairs": {}, "runs": 0}  # "a|b" -> {occurrences, successes}

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(self._data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("complementarity save failed: %s", exc)

    @staticmethod
    def _pair_key(a: str, b: str) -> str:
        return "|".join(sorted((a, b)))

    def record_run(self, tools: List[str], success: bool) -> None:
        """Record one task run: its tool set and outcome."""
        unique = sorted({t for t in tools if t})
        if len(unique) < 2:
            return
        with self._lock:
            self._data["runs"] = int(self._data.get("runs", 0)) + 1
            for a, b in itertools.combinations(unique, 2):
                key = self._pair_key(a, b)
                entry = self._data["pairs"].setdefault(
                    key, {"occurrences": 0, "successes": 0}
                )
                entry["occurrences"] = int(entry.get("occurrences", 0)) + 1
                if success:
                    entry["successes"] = int(entry.get("successes", 0)) + 1
            self._save()

    def pair_stats(self, a: str, b: str) -> Dict[str, Any]:
        key = self._pair_key(a, b)
        with self._lock:
            entry = self._data["pairs"].get(key)
            if entry is None:
                return {"occurrences": 0, "successes": 0, "success_rate": None}
            occurrences = int(entry.get("occurrences", 0))
            successes = int(entry.get("successes", 0))
            return {
                "occurrences": occurrences,
                "successes": successes,
                "success_rate": successes / occurrences if occurrences else None,
            }

    def complements(
        self, tool: str, min_occurrences: int = MIN_PAIR_OCCURRENCES
    ) -> List[Tuple[str, float]]:
        """Tools that pair with `tool`, ranked by success rate.

        Returns [(other_tool, success_rate)] with at least
        min_occurrences co-occurrences, best first.
        """
        results: List[Tuple[str, float]] = []
        with self._lock:
            for key, entry in self._data["pairs"].items():
                a, b = key.split("|")
                if tool not in (a, b):
                    continue
                occurrences = int(entry.get("occurrences", 0))
                if occurrences < min_occurrences:
                    continue
                successes = int(entry.get("successes", 0))
                results.append(
                    (b if a == tool else a, successes / occurrences)
                )
        return sorted(results, key=lambda kv: (-kv[1], kv[0]))

    def run_count(self) -> int:
        with self._lock:
            return int(self._data.get("runs", 0))

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return json.loads(json.dumps(self._data))
