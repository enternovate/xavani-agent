# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.


"""G04: follow-up question queue.

When a turn ends with an open question (the agent asked the user
something and the turn completed without an answer), the question is
queued here instead of being lost.  The CLI surfaces pending questions
at the start of a later session so they are answered at a good moment
instead of blocking the task that just finished.

Storage is an append-only JSONL under the Xavani home; every method is
best-effort and never raises.
"""

from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from xavani_constants import get_xavani_home

logger = logging.getLogger(__name__)
try:
    from xavani_cli.safe_logging import SafeLogFilter
    SafeLogFilter.install()
except Exception:
    pass


class FollowUpQueue:
    """JSONL-backed queue of open follow-up questions."""

    def __init__(self, path: Optional[str] = None) -> None:
        self._path = path or str(get_xavani_home() / "followups.jsonl")
        self._lock = threading.Lock()

    def record(self, question: str, session_id: str = "") -> bool:
        """Append one open question.  Best-effort; never raises."""
        text = (question or "").strip()
        if not text:
            return False
        entry: Dict[str, Any] = {
            "id": uuid.uuid4().hex,
            "question": text[:2000],
            "session_id": session_id or "",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "answered": False,
        }
        try:
            with self._lock:
                with open(self._path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            return True
        except OSError as exc:
            logger.warning("Follow-up queue write failed: %s", exc)
            return False

    def pending(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Return the oldest unanswered questions, at most ``limit``."""
        rows: List[Dict[str, Any]] = []
        try:
            with self._lock:
                with open(self._path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            row = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if not row.get("answered"):
                            rows.append(row)
        except OSError:
            return []
        return rows[:limit]

    def mark_answered(self, question_id: str) -> bool:
        """Mark one queued question as answered.  Best-effort."""
        if not question_id:
            return False
        found = False
        try:
            with self._lock:
                rows: List[Dict[str, Any]] = []
                with open(self._path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            row = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if row.get("id") == question_id:
                            row["answered"] = True
                            found = True
                        rows.append(row)
                with open(self._path, "w", encoding="utf-8") as f:
                    for row in rows:
                        f.write(json.dumps(row, ensure_ascii=False) + "\n")
            return found
        except OSError as exc:
            logger.warning("Follow-up queue update failed: %s", exc)
            return False
