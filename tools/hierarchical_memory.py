# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""B14: hierarchical memory.

Three-tier memory with explicit promotion:

1. WORKING: the current session's context (short-lived, session-scoped)
2. EPISODIC: task outcomes (medium-lived, cross-session recall)
3. PROCEDURAL: proven patterns (long-lived, skill-like knowledge)

Memories promote up a tier when they prove themselves (outcome
success) and decay down when they go stale. The promotion rule is
deterministic and auditable: an episode with a successful outcome and
repeated occurrence promotes to procedural.

Usage::

    from tools.hierarchical_memory import HierarchicalMemory

    hm = HierarchicalMemory(home_dir)
    hm.store_working("session-1", "currently fixing auth")
    hm.store_episodic("task:auth-fix", outcome="success")
    hm.promote_if_ready("task:auth-fix")
    hm.promote_if_ready("task:auth-fix")  # 2nd success -> procedural
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

TIERS = ("working", "episodic", "procedural")

# An episodic memory promotes to procedural after this many successes.
PROMOTION_SUCCESSES = 2
# Working memories older than this are dropped (seconds).
WORKING_TTL_SECONDS = 24 * 3600


class HierarchicalMemory:
    """Deterministic three-tier memory store (thread-safe)."""

    def __init__(self, home: Optional[Path] = None):
        self._home = home if home is not None else Path(
            os.environ.get("XAVANI_HOME", "~/.xavani")
        ).expanduser()
        self._path = self._home / "data" / "hierarchical_memory.json"
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        try:
            if self._path.exists():
                return json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("hierarchical memory load failed: %s", exc)
        return {"working": {}, "episodic": {}, "procedural": {}}

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(self._data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("hierarchical memory save failed: %s", exc)

    # ── working tier ────────────────────────────────────────────────

    def store_working(self, session_id: str, content: str) -> None:
        with self._lock:
            self._data["working"][session_id] = {
                "content": content,
                "ts": time.time(),
            }
            self._save()

    def working(self, session_id: str) -> Optional[str]:
        with self._lock:
            entry = self._data["working"].get(session_id)
            if entry is None:
                return None
            if time.time() - entry["ts"] > WORKING_TTL_SECONDS:
                self._data["working"].pop(session_id, None)
                self._save()
                return None
            return entry["content"]

    # ── episodic tier ───────────────────────────────────────────────

    def store_episodic(self, key: str, outcome: str, note: str = "") -> None:
        """Store/refresh an episodic memory. Outcome: success | failure."""
        with self._lock:
            entry = self._data["episodic"].get(key, {
                "key": key,
                "successes": 0,
                "failures": 0,
                "last_outcome": "",
                "note": "",
                "ts": 0,
            })
            if outcome == "success":
                entry["successes"] = int(entry.get("successes", 0)) + 1
            elif outcome == "failure":
                entry["failures"] = int(entry.get("failures", 0)) + 1
            entry["last_outcome"] = outcome
            if note:
                entry["note"] = note
            entry["ts"] = time.time()
            self._data["episodic"][key] = entry
            self._save()

    def episodic(self, key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            entry = self._data["episodic"].get(key)
            return dict(entry) if entry else None

    # ── promotion ───────────────────────────────────────────────────

    def promote_if_ready(self, key: str) -> bool:
        """Promote an episodic memory to procedural after N successes.

        Returns True when the promotion happened.
        """
        with self._lock:
            entry = self._data["episodic"].get(key)
            if entry is None:
                return False
            if int(entry.get("successes", 0)) < PROMOTION_SUCCESSES:
                return False
            # Promote: copy into procedural, drop from episodic.
            self._data["procedural"][key] = {
                "key": key,
                "note": entry.get("note", ""),
                "successes": entry.get("successes"),
                "promoted_at": time.time(),
            }
            self._data["episodic"].pop(key, None)
            self._save()
            return True

    def procedural(self, key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            entry = self._data["procedural"].get(key)
            return dict(entry) if entry else None

    def all_procedural(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [dict(v) for v in self._data["procedural"].values()]

    def tier_counts(self) -> Dict[str, int]:
        with self._lock:
            return {
                tier: len(self._data[tier]) for tier in TIERS
            }

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return json.loads(json.dumps(self._data))
