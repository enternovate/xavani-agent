# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Periodic retention of completed turns in curated long-term memory."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from utils import atomic_replace


_MAX_USER_CHARS = 700
_MAX_ASSISTANT_CHARS = 1_300
_STATE_VERSION = 1
_STATE_FILE_PREFIX = ".turn_bank_"
_BANK_HEADER_RE = re.compile(r"^\[Long-term turn bank — (\d+) completed turns\]\n\n")


def parse_turn_bank_interval(value: Any) -> int:
    """Return a positive turn-bank interval, or zero when disabled."""
    try:
        interval = int(value)
    except (TypeError, ValueError):
        return 0
    return interval if interval > 0 else 0


def _message_text(message: Dict[str, Any]) -> str:
    content = message.get("content", "")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return "\n".join(
            str(part.get("text", "")).strip()
            for part in content
            if isinstance(part, dict) and part.get("type") == "text" and part.get("text")
        ).strip()
    return str(content or "").strip()


def completed_turns_from_messages(messages: Iterable[Dict[str, Any]]) -> List[Tuple[str, str]]:
    """Extract completed user/assistant pairs, ignoring tool-loop messages."""
    turns: List[Tuple[str, str]] = []
    pending_user: str | None = None
    for message in messages or []:
        if not isinstance(message, dict):
            continue
        role = message.get("role")
        if role == "user":
            pending_user = _message_text(message)
        elif role == "assistant" and pending_user is not None:
            if message.get("tool_calls"):
                continue
            assistant = _message_text(message)
            if assistant:
                turns.append((pending_user, assistant))
                pending_user = None
    return turns


def _state_path(agent: Any) -> Path | None:
    explicit = getattr(agent, "_turn_bank_state_path", None)
    if explicit:
        return Path(explicit)

    session_id = getattr(agent, "session_id", None)
    if not session_id:
        return None
    try:
        from tools.memory_tool import get_memory_dir

        digest = hashlib.sha256(str(session_id).encode("utf-8")).hexdigest()[:24]
        return get_memory_dir() / f"{_STATE_FILE_PREFIX}{digest}.json"
    except Exception:
        return None


def _read_state(agent: Any) -> Dict[str, int] | None:
    path = _state_path(agent)
    if path is None:
        return None
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
        if state.get("version") != _STATE_VERSION:
            return None
        completed_count = int(state["completed_count"])
        pending_count = int(state["pending_count"])
        if completed_count < 0 or pending_count < 0:
            return None
        return {
            "completed_count": completed_count,
            "pending_count": pending_count,
        }
    except (OSError, TypeError, ValueError, KeyError, AttributeError):
        return None


def _bank_body(turns: Iterable[Tuple[str, str]]) -> str:
    return "\n\n".join(_format_turn(user, assistant) for user, assistant in turns)


def _persisted_prefix_length(
    turns: List[Tuple[str, str]], interval: int, store: Any
) -> int:
    entries = getattr(store, "memory_entries", ())
    if not isinstance(entries, (list, tuple, set)):
        return 0
    bank_bodies = {
        entry[match.end():]
        for entry in entries
        if isinstance(entry, str)
        and (match := _BANK_HEADER_RE.match(entry)) is not None
    }
    fallback_turns = {
        _format_turn(user, assistant) for user, assistant in turns
    }
    fallback_entries = {
        entry for entry in entries if isinstance(entry, str) and entry in fallback_turns
    }
    persisted_end = 0
    while persisted_end < len(turns):
        matches = [
            end
            for end in range(persisted_end + interval, len(turns) + 1)
            if _bank_body(turns[persisted_end:end]) in bank_bodies
        ]
        if matches:
            persisted_end = max(matches)
            continue
        if _format_turn(*turns[persisted_end]) in fallback_entries:
            persisted_end += 1
            continue
        break
    return persisted_end


def _write_state(agent: Any, completed_count: int, pending_count: int) -> None:
    path = _state_path(agent)
    if path is None:
        return

    payload = {
        "version": _STATE_VERSION,
        "completed_count": max(0, int(completed_count)),
        "pending_count": max(0, int(pending_count)),
    }
    tmp_path: str | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=str(path.parent), prefix=f"{path.name}.", suffix=".tmp"
        )
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
        atomic_replace(tmp_path, path)
        tmp_path = None
    except Exception:
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def hydrate_turn_bank(agent: Any, messages: Iterable[Dict[str, Any]]) -> None:
    """Restore the turn-bank counter and remainder for a fresh agent instance."""
    interval = parse_turn_bank_interval(getattr(agent, "_turn_bank_interval", 0))
    if (
        interval <= 0
        or not getattr(agent, "_memory_store", None)
        or getattr(agent, "_turn_bank_completed_count", 0) != 0
        or getattr(agent, "_turn_bank_pending", None)
    ):
        return

    turns = completed_turns_from_messages(messages)
    state = _read_state(agent)
    if state is not None:
        agent._turn_bank_completed_count = state["completed_count"]
        pending_count = min(state["pending_count"], len(turns))
        agent._turn_bank_pending = list(turns[-pending_count:]) if pending_count else []
        return

    agent._turn_bank_completed_count = len(turns)
    persisted_end = _persisted_prefix_length(turns, interval, agent._memory_store)
    agent._turn_bank_pending = list(turns[persisted_end:])


def _format_turn(user_text: str, assistant_text: str) -> str:
    user = (user_text or "").strip()[:_MAX_USER_CHARS]
    assistant = (assistant_text or "").strip()[:_MAX_ASSISTANT_CHARS]
    return f"User: {user}\nAssistant: {assistant}"


def _build_bank_content(turns: Iterable[Tuple[str, str]], turn_count: int) -> str:
    content = f"[Long-term turn bank — {turn_count} completed turns]\n\n"
    content += "\n\n".join(_format_turn(user, assistant) for user, assistant in turns)
    return content


def _memory_write_succeeded(result: Any) -> bool:
    try:
        parsed = json.loads(result) if isinstance(result, str) else result
    except (TypeError, ValueError, json.JSONDecodeError):
        return False
    return isinstance(parsed, dict) and parsed.get("success") is True and parsed.get("staged") is not True


def _available_memory_chars(store: Any) -> int | None:
    try:
        limit = int(getattr(store, "memory_char_limit"))
    except (TypeError, ValueError):
        return None
    try:
        current = int(store._char_count("memory"))
    except (AttributeError, TypeError, ValueError):
        current = 0
    return max(0, limit - current)


def _write_pending_turns(agent: Any, pending: List[Tuple[str, str]], completed_count: int) -> bool:
    from tools.memory_tool import memory_tool

    store = agent._memory_store
    content = _build_bank_content(pending, completed_count)
    available = _available_memory_chars(store)
    if available is None or len(content) <= available:
        try:
            return _memory_write_succeeded(
                memory_tool(
                    action="add",
                    target="memory",
                    content=content,
                    store=store,
                )
            )
        except Exception:
            return False

    for user_text, assistant_text in pending:
        try:
            if not _memory_write_succeeded(
                memory_tool(
                    action="add",
                    target="memory",
                    content=_format_turn(user_text, assistant_text),
                    store=store,
                )
            ):
                return False
        except Exception:
            return False
    return True


def add_completed_turn(agent: Any, user_text: str, assistant_text: str) -> bool:
    """Retain a completed turn when the configured bank boundary is reached."""
    interval = parse_turn_bank_interval(getattr(agent, "_turn_bank_interval", 0))
    if interval <= 0 or not getattr(agent, "_memory_store", None):
        return False

    pending = list(getattr(agent, "_turn_bank_pending", []) or [])
    pending.append((str(user_text or ""), str(assistant_text or "")))
    completed_count = int(getattr(agent, "_turn_bank_completed_count", 0)) + 1
    if completed_count % interval:
        agent._turn_bank_completed_count = completed_count
        agent._turn_bank_pending = pending
        _write_state(agent, completed_count, len(pending))
        return False

    agent._turn_bank_pending = pending
    _write_state(agent, completed_count - 1, len(pending))
    if not _write_pending_turns(agent, pending, completed_count):
        return False

    agent._turn_bank_completed_count = completed_count
    agent._turn_bank_pending = []
    _write_state(agent, completed_count, 0)
    return True


__all__ = [
    "add_completed_turn",
    "completed_turns_from_messages",
    "hydrate_turn_bank",
    "parse_turn_bank_interval",
]
