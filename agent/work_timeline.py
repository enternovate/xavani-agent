# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Local work timeline (R2 Task 22).

A deterministic, append-only record of what the agent did, stored BESIDE
the current session log (``<session>.timeline.jsonl`` next to
``<session>.json`` in the existing sessions directory — no new transcript
database). Every write goes through :func:`record_event`, which sanitizes
first:

* raw credentials, tokens, passwords, auth headers, and full environment
  dictionaries are dropped by key;
* hidden reasoning / scratchpad fields are dropped;
* string values are truncated (full file contents are not stored by
  default);
* values must stay JSON-safe primitives.

Recorded event types (plan Task 22): ``task.started``, ``skill.loaded``,
``tool.started``, ``tool.completed``, ``artifact.changed``,
``verification.completed``, ``approval.requested``, ``approval.resolved``,
``task.blocked``, ``task.completed``.

``approval.requested`` / ``approval.resolved`` are recorded by the operator
audit chain (Task 19) and are mirrored here once the operator runs with an
agent-attached session; the type list is enforced regardless.

Replay is READ-ONLY: :func:`replay` returns copies and performs no work —
a replayed timeline can never execute a tool.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Iterable

EVENT_TYPES = (
    "task.started",
    "skill.loaded",
    "tool.started",
    "tool.completed",
    "artifact.changed",
    "verification.completed",
    "approval.requested",
    "approval.resolved",
    "task.blocked",
    "task.completed",
)

# Dropped by key (case-insensitive): credentials, headers, environments,
# and hidden reasoning are never part of the timeline.
_EXCLUDED_KEYS = frozenset({
    "api_key", "apikey", "token", "access_token", "refresh_token",
    "password", "passwd", "secret", "client_secret", "authorization",
    "auth", "headers", "header", "env", "environment", "environ",
    "reasoning", "thinking", "scratchpad", "chain_of_thought",
})

_MAX_VALUE_LEN = 240


def _sessions_dir() -> Path:
    """The active XAVANI_HOME sessions directory (profile-aware)."""
    try:
        from xavani_constants import get_xavani_home

        return get_xavani_home() / "sessions"
    except Exception:
        import os

        return Path(os.path.expanduser("~/.xavani")) / "sessions"


def _sanitize(fields: dict[str, Any]) -> dict[str, Any]:
    """Drop excluded keys, truncate long values, keep primitives JSON-safe."""
    out: dict[str, Any] = {}
    for key, value in (fields or {}).items():
        name = str(key).lower()
        if name in _EXCLUDED_KEYS:
            continue
        if value is None or isinstance(value, (bool, int, float)):
            out[name] = value
            continue
        text = value if isinstance(value, str) else str(value)
        out[name] = text if len(text) <= _MAX_VALUE_LEN else text[:_MAX_VALUE_LEN] + "…"
    return out


def timeline_path(agent) -> Path | None:
    """The timeline file beside the agent's session log, or None."""
    log = getattr(agent, "session_log_file", None)
    if not log:
        return None
    path = Path(log)
    return path.with_name(path.stem + ".timeline.jsonl")


def record_event(agent, event_type: str, **fields: Any) -> dict[str, Any] | None:
    """Append one sanitized timeline event; returns the record or None."""
    if event_type not in EVENT_TYPES:
        raise ValueError(f"unknown timeline event: {event_type!r}")
    path = timeline_path(agent)
    if path is None:
        return None
    record = {"ts": time.time(), "type": event_type, **_sanitize(fields)}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    except OSError:
        return None  # the timeline must never break the work it records
    return record


def read_timeline(path) -> list[dict[str, Any]]:
    """Read a timeline file; unparseable lines are skipped, never fatal."""
    target = Path(path)
    if not target.is_file():
        return []
    entries: list[dict[str, Any]] = []
    try:
        for line in target.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except OSError:
        return []
    return entries


def replay(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Read-only replay: return copies of the events, execute nothing."""
    return [dict(event) for event in events]


def latest_timeline_file(sessions_dir=None) -> Path | None:
    """The most recently modified timeline file (for the desktop view)."""
    directory = Path(sessions_dir) if sessions_dir else _sessions_dir()
    if not directory.is_dir():
        return None
    files = sorted(
        directory.glob("*.timeline.jsonl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return files[0] if files else None
