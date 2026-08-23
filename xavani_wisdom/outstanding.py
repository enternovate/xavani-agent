#!/usr/bin/env python3

# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""
Outstanding-work ledger — cross-session memory of unfinished items.

Append-only JSONL at ``$XAVANI_HOME/outstanding.jsonl``. Entries:
``{n, ts, session_id, kind, text, status}`` where kind is goal|loop|todo
and status is open|done|cancelled. The desktop reminder surface and the
CLI /outstanding command both read from here. Items stay open — and keep
reminding — until explicitly closed with /done or /outstanding done N.
"""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

XAVANI_HOME = Path(os.environ.get("XAVANI_HOME") or Path.home() / ".xavani")
DEFAULT_PATH = XAVANI_HOME / "outstanding.jsonl"

VALID_KINDS = {"goal", "loop", "todo"}
VALID_STATUSES = {"open", "done", "cancelled"}


class OutstandingLedger:
    """JSONL-backed list of outstanding work items."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path else DEFAULT_PATH

    # -- io -------------------------------------------------------------

    def _read_all(self) -> List[Dict[str, Any]]:
        try:
            raw = self.path.read_text(encoding="utf-8")
        except OSError:
            return []
        out = []
        for line in raw.splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if isinstance(entry, dict):
                out.append(entry)
        return out

    def _write_all(self, entries: List[Dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        body = "".join(
            json.dumps(e, ensure_ascii=False) + "\n" for e in entries
        )
        fd, tmp_name = tempfile.mkstemp(
            dir=str(self.path.parent), prefix=".outstanding-", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(body)
            os.chmod(tmp_name, 0o600)
            os.replace(tmp_name, self.path)
        except OSError:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

    def _next_n(self, entries: List[Dict[str, Any]]) -> int:
        return max((e.get("n", 0) for e in entries), default=0) + 1

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    # -- public api -------------------------------------------------------

    def add(
        self,
        text: str,
        kind: str = "goal",
        session_id: str = "",
    ) -> Dict[str, Any]:
        kind = str(kind).strip().lower()
        if kind not in VALID_KINDS:
            kind = "goal"
        entries = self._read_all()
        entry: Dict[str, Any] = {
            "n": self._next_n(entries),
            "ts": self._now(),
            "session_id": str(session_id),
            "kind": kind,
            "text": str(text).strip(),
            "status": "open",
        }
        entries.append(entry)
        self._write_all(entries)
        return entry

    def items(self, include_closed: bool = False) -> List[Dict[str, Any]]:
        entries = self._read_all()
        # Collapse duplicate n keeping the LAST occurrence (latest state).
        latest: Dict[int, Dict[str, Any]] = {}
        order: List[int] = []
        for e in entries:
            n = int(e.get("n", 0))
            if n not in latest:
                order.append(n)
            latest[n] = e
        out = [latest[n] for n in sorted(order)]
        if include_closed:
            return out
        return [e for e in out if e.get("status") == "open"]

    def set_status(self, n: int, status: str) -> Optional[Dict[str, Any]]:
        status = str(status).strip().lower()
        if status not in VALID_STATUSES:
            return None
        entries = self._read_all()
        result: Optional[Dict[str, Any]] = None
        for e in entries:
            if int(e.get("n", -1)) == int(n):
                e["status"] = status
                e["closed_ts"] = self._now()
                result = e
        if result is not None:
            self._write_all(entries)
        return result

    def open_count(self) -> int:
        return len(self.items())
