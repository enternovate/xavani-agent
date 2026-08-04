# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""G06: agent-initiated continuation.

Lets the agent mark a task as unfinished and request that the NEXT
session continue it. The continuation store persists the task summary,
the stopping point, and any recovery hints. On session start, the
context prefetch (G08) injects pending continuations so the agent picks
the work back up instead of losing it.

Usage::

    from tools.continuation_store import ContinuationStore

    store = ContinuationStore()
    store.request_continuation(
        session_id="s1",
        task_summary="Finish the auth refactor",
        stopping_point="mid-file at auth.py:120",
        hints=["Run tests first"],
    )
    pending = store.pending()
    store.resolve("s1", "completed")
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

STATUSES = ("pending", "resolved", "abandoned")


class ContinuationStore:
    """Persistent continuation requests (thread-safe)."""

    def __init__(self, home: Optional[Path] = None):
        self._home = home if home is not None else Path(
            os.environ.get("XAVANI_HOME", "~/.xavani")
        ).expanduser()
        self._path = self._home / "data" / "continuations.json"
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        try:
            if self._path.exists():
                return json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("continuation load failed: %s", exc)
        return {"continuations": {}}

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(self._data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("continuation save failed: %s", exc)

    def request_continuation(
        self,
        session_id: str,
        task_summary: str,
        *,
        stopping_point: str = "",
        hints: Optional[List[str]] = None,
    ) -> str:
        """Record a continuation request. Returns the continuation id."""
        continuation_id = f"{session_id}-{int(time.time())}"
        with self._lock:
            self._data["continuations"][continuation_id] = {
                "id": continuation_id,
                "session_id": session_id,
                "task_summary": task_summary,
                "stopping_point": stopping_point,
                "hints": list(hints or []),
                "status": "pending",
                "created_at": time.time(),
                "resolved_at": None,
            }
            self._save()
            return continuation_id

    def pending(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Pending continuations, newest first."""
        with self._lock:
            entries = [
                dict(e) for e in self._data["continuations"].values()
                if e.get("status") == "pending"
            ]
        return sorted(entries, key=lambda e: -e["created_at"])[:limit]

    def resolve(self, continuation_id: str, status: str = "completed") -> bool:
        """Mark a continuation resolved or abandoned."""
        if status not in STATUSES or status == "pending":
            return False
        with self._lock:
            entry = self._data["continuations"].get(continuation_id)
            if entry is None:
                return False
            entry["status"] = status
            entry["resolved_at"] = time.time()
            self._save()
            return True

    def pending_count(self) -> int:
        with self._lock:
            return sum(
                1 for e in self._data["continuations"].values()
                if e.get("status") == "pending"
            )

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return json.loads(json.dumps(self._data))
