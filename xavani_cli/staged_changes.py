# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Staged multi-file changes: review before apply.

Tools or commands stage proposed file writes here instead of touching
disk. /diff renders the pending set, /apply executes it in order,
/reject drops all or one entry. Nothing writes until apply.
"""

from __future__ import annotations

import threading
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

_write_staging: ContextVar[bool] = ContextVar(
    "xavani_write_staging", default=False
)


def staging_enabled() -> bool:
    """True when writes should queue for review instead of touching disk."""
    return _write_staging.get()


def enable_staging() -> None:
    _write_staging.set(True)


def disable_staging() -> None:
    _write_staging.set(False)


@dataclass
class StagedWrite:
    path: str
    content: str
    reason: str = ""
    sequence: int = field(default=0)


class StagedChangeSet:
    """Thread-safe pending-write registry for one session."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._writes: List[StagedWrite] = []
        self._counter = 0

    def stage(self, path: str, content: str, reason: str = "") -> int:
        with self._lock:
            self._counter += 1
            self._writes.append(
                StagedWrite(
                    path=path, content=content, reason=reason,
                    sequence=self._counter,
                )
            )
            return self._counter

    def pending(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "seq": w.sequence, "path": w.path,
                    "reason": w.reason, "bytes": len(w.content.encode("utf-8")),
                }
                for w in self._writes
            ]

    def render_diff_summary(self) -> str:
        rows = self.pending()
        if not rows:
            return "No staged changes."
        lines = [f"{'seq':>4}  {'bytes':>7}  path"]
        for row in rows:
            note = f" ({row['reason']})" if row["reason"] else ""
            lines.append(f"{row['seq']:>4}  {row['bytes']:>7}  {row['path']}{note}")
        total = sum(r["bytes"] for r in rows)
        lines.append(f"  {len(rows)} file(s), {total} bytes staged")
        return "\n".join(lines)

    def apply(self, base_dir: Optional[Path] = None) -> List[str]:
        """Write every staged file in order; returns applied paths."""
        applied: List[str] = []
        with self._lock:
            batch = list(self._writes)
            self._writes.clear()
        for write in batch:
            target = Path(write.path)
            if base_dir is not None and not target.is_absolute():
                target = base_dir / target
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(write.content, encoding="utf-8")
            applied.append(str(target))
        return applied

    def reject(self, seq: Optional[int] = None) -> int:
        """Drop one staged write by seq, or everything when None."""
        with self._lock:
            if seq is None:
                dropped = len(self._writes)
                self._writes.clear()
                return dropped
            before = len(self._writes)
            self._writes = [w for w in self._writes if w.sequence != seq]
            return before - len(self._writes)


_SESSION_SETS: Dict[int, StagedChangeSet] = {}
_REGISTRY_LOCK = threading.Lock()


def get_change_set(session_key: int = 0) -> StagedChangeSet:
    with _REGISTRY_LOCK:
        if session_key not in _SESSION_SETS:
            _SESSION_SETS[session_key] = StagedChangeSet()
        return _SESSION_SETS[session_key]
