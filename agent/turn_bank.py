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
_LEGACY_STATE_VERSION = 1
_STATE_VERSION = 2
_SUPPORTED_STATE_VERSIONS = {_LEGACY_STATE_VERSION, _STATE_VERSION}
_FUTURE_STATE_BARRIER = object()
_STATE_FILE_PREFIX = ".turn_bank_"
_BANK_HEADER_RE = re.compile(r"^\[Long-term turn bank — (\d+) completed turns\]\n\n")
_COMPACTION_ENVELOPE_MARKER = "[CONTEXT COMPACTION — REFERENCE ONLY]"
_SUMMARY_END_MARKER = (
    "\n\n--- END OF CONTEXT SUMMARY — respond to the message below, "
    "not the summary above ---"
)
_TASK_LIST_PRESERVED_MARKER = (
    "[Your active task list was preserved across context compression]"
)
_LENGTH_CONTINUATION_MARKER = (
    "[System: Your previous response was truncated by the output length limit. "
    "Continue exactly where you left off. Do not restart or repeat prior text. "
    "Finish the answer directly.]"
)
_CODEX_ACK_CONTINUATION_MARKER = (
    "[System: Continue now. Execute the required tool calls and only send "
    "your final answer after completing the task.]"
)
_MAX_ITERATION_MARKER = (
    "You've reached the maximum number of tool-calling iterations allowed. "
    "Please provide a final response summarizing what you've found and "
    "accomplished so far, without calling any more tools."
)
_KANBAN_STOP_NUDGE_PREFIX = "[System: You are a Xavani kanban worker."
_EMPTY_RECOVERY_NUDGE_MARKER = (
    "You just executed tool calls but returned an "
    "empty response. Please process the tool "
    "results above and continue with the task."
)
_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
_EMPTY_ASSISTANT_SENTINEL = "(empty)"
_MCP_RELOAD_PREFIX = "[IMPORTANT: MCP servers have been reloaded."


def _strip_context_summary(text: str) -> str:
    _, _, suffix = text.rpartition(_SUMMARY_END_MARKER)
    return suffix.strip()


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
    assistant_parts: List[str] = []
    for message in messages or []:
        if not isinstance(message, dict):
            continue
        role = message.get("role")
        if role == "user":
            text = _message_text(message)
            if _COMPACTION_ENVELOPE_MARKER in text:
                if _SUMMARY_END_MARKER in text:
                    text = _strip_context_summary(text)
                else:
                    text = ""
            if text == _TASK_LIST_PRESERVED_MARKER:
                if pending_user is not None and assistant_parts:
                    turns.append((pending_user, "".join(assistant_parts)))
                assistant_parts = []
                pending_user = None
                continue
            if text == _LENGTH_CONTINUATION_MARKER and pending_user is not None:
                continue
            if text == _CODEX_ACK_CONTINUATION_MARKER and pending_user is not None:
                assistant_parts = []
                continue
            if text == _MAX_ITERATION_MARKER and pending_user is not None:
                assistant_parts = []
                pending_user = None
                continue
            if text.startswith(_KANBAN_STOP_NUDGE_PREFIX) and pending_user is not None:
                assistant_parts = []
                continue
            if text == _EMPTY_RECOVERY_NUDGE_MARKER and pending_user is not None:
                assistant_parts = []
                continue
            if text.startswith(_MCP_RELOAD_PREFIX) and "\n" not in text:
                continue
            if pending_user is not None and assistant_parts:
                turns.append((pending_user, "".join(assistant_parts)))
            assistant_parts = []
            pending_user = text or None
        elif role == "assistant" and pending_user is not None:
            if message.get("tool_calls"):
                continue
            if message.get("_thinking_prefill"):
                continue
            if message.get("_empty_terminal_sentinel"):
                continue
            assistant = _message_text(message)
            if not assistant or _COMPACTION_ENVELOPE_MARKER in assistant:
                continue
            if assistant == _EMPTY_ASSISTANT_SENTINEL:
                continue
            if not _THINK_BLOCK_RE.sub("", assistant).strip():
                continue
            assistant_parts.append(assistant)
    if pending_user is not None and assistant_parts:
        turns.append((pending_user, "".join(assistant_parts)))
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


def _read_state(
    agent: Any, path: Path | None = None
) -> Dict[str, Any] | object | None:
    if path is None:
        path = _state_path(agent)
    if path is None:
        return None
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
        version = state.get("version")
        if not isinstance(version, int):
            return None
        if version > _STATE_VERSION:
            return _FUTURE_STATE_BARRIER
        if version < _LEGACY_STATE_VERSION:
            return None
        raw_completed = state.get("completed_count")
        raw_pending = state.get("pending_count")
        if not _is_count(raw_completed) or not _is_count(raw_pending):
            return None
        completed_count = raw_completed
        pending_count = raw_pending
        if version == _LEGACY_STATE_VERSION:
            raw_persisted = state.get("persisted_count", 0)
            if not _is_count(raw_persisted):
                return None
            persisted_count = raw_persisted
            if (
                completed_count < 0
                or pending_count < 0
                or persisted_count < 0
                or persisted_count > pending_count
            ):
                return None
            return {
                "version": version,
                "completed_count": completed_count,
                "pending_count": pending_count,
                "persisted_count": persisted_count,
            }
        checkpoint_digest = state.get("checkpoint_digest")
        pending_digest = state.get("pending_digest")
        write_due = state.get("write_due")
        if (
            not _is_sha256_digest(checkpoint_digest)
            or not _is_sha256_digest(pending_digest)
            or not isinstance(write_due, bool)
            or completed_count < 0
            or pending_count < 0
            or pending_count > completed_count
        ):
            return None
        return {
            "version": version,
            "completed_count": completed_count,
            "pending_count": pending_count,
            "checkpoint_digest": checkpoint_digest,
            "pending_digest": pending_digest,
            "write_due": write_due,
        }
    except (OSError, TypeError, ValueError, KeyError, AttributeError):
        return None


def _ancestor_sidecar_path(agent: Any, session_id: Any) -> Path:
    explicit = getattr(agent, "_turn_bank_state_path", None)
    if explicit:
        base_dir = Path(explicit).parent
    else:
        from tools.memory_tool import get_memory_dir

        base_dir = get_memory_dir()
    digest = hashlib.sha256(str(session_id).encode("utf-8")).hexdigest()[:24]
    return base_dir / f"{_STATE_FILE_PREFIX}{digest}.json"


def _valid_compression_parent(
    agent: Any, session_db: Any, child_id: Any, parent_id: Any
) -> bool:
    session_getter = getattr(session_db, "get_session", None)
    if session_getter is None:
        return False
    try:
        parent = session_getter(parent_id) or {}
        child = session_getter(child_id) or {}
    except Exception:
        return False
    if not parent or not child:
        return False
    if parent.get("end_reason") != "compression":
        return False
    child_start = child.get("started_at")
    parent_end = parent.get("ended_at")
    if child_start is None or parent_end is None:
        return False
    return child_start >= parent_end


def _read_lineage_state(agent: Any) -> Dict[str, Any] | object | None:
    current = _read_state(agent)
    if current is _FUTURE_STATE_BARRIER or isinstance(current, dict):
        return current
    session_db = getattr(agent, "_session_db", None)
    session_id = getattr(agent, "session_id", None)
    parent_id = getattr(agent, "_parent_session_id", None)
    if not session_db or not session_id or not parent_id:
        return current
    seen = set()
    child_id = session_id
    while parent_id and parent_id not in seen:
        seen.add(parent_id)
        if not _valid_compression_parent(agent, session_db, child_id, parent_id):
            break
        ancestor_path = _ancestor_sidecar_path(agent, parent_id)
        if ancestor_path.exists():
            ancestor_state = _read_state(agent, ancestor_path)
            if ancestor_state is _FUTURE_STATE_BARRIER:
                return _FUTURE_STATE_BARRIER
            if isinstance(ancestor_state, dict):
                return ancestor_state
            return None
        parent_row = session_db.get_session(parent_id) or {}
        child_id = parent_id
        parent_id = parent_row.get("parent_session_id")
    return current



def _bank_body(turns: Iterable[Tuple[str, str]]) -> str:
    return "\n\n".join(_format_turn(user, assistant) for user, assistant in turns)


def _persisted_prefix_length(
    turns: List[Tuple[str, str]],
    interval: int,
    store: Any,
    base_count: int = 0,
) -> int:
    entries = getattr(store, "memory_entries", ())
    if not isinstance(entries, (list, tuple, set)):
        return 0
    bank_bodies: Dict[str, int] = {}
    for entry in entries:
        if isinstance(entry, str) and (match := _BANK_HEADER_RE.match(entry)):
            bank_bodies[entry[match.end():]] = int(match.group(1))
    fallback_counts: Dict[str, int] = {}
    for entry in entries:
        if isinstance(entry, str):
            fallback_counts[entry] = fallback_counts.get(entry, 0) + 1
    formatted = [_format_turn(user, assistant) for user, assistant in turns]
    persisted_end = 0
    while persisted_end < len(turns):
        matches = [
            end
            for end in range(persisted_end + interval, len(turns) + 1)
            if bank_bodies.get(_bank_body(turns[persisted_end:end]))
            == base_count + end
        ]
        if matches:
            persisted_end = max(matches)
            continue
        text = formatted[persisted_end]
        prior = sum(1 for k in range(persisted_end) if formatted[k] == text)
        if fallback_counts.get(text, 0) > prior:
            persisted_end += 1
            continue
        break
    return persisted_end


_TURN_DIGEST_PREFIX = "xavani-turn-bank-turn-v2\x00"
_CHECKPOINT_DIGEST_PREFIX = "xavani-turn-bank-checkpoint-v2\x00"
_PENDING_DIGEST_PREFIX = "xavani-turn-bank-pending-v2\x00"
_HEX_DIGITS = frozenset("0123456789abcdef")


def _turn_digest(user_text: str, assistant_text: str) -> str:
    formatted = _format_turn(user_text, assistant_text)
    return hashlib.sha256(_TURN_DIGEST_PREFIX.encode() + formatted.encode()).hexdigest()


def _checkpoint_digest(completed_count: int, turn_digest: str) -> str:
    payload = json.dumps(
        [int(completed_count), turn_digest],
        ensure_ascii=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(
        _CHECKPOINT_DIGEST_PREFIX.encode() + payload.encode()
    ).hexdigest()


def _pending_digest(completed_count: int, pending: Iterable[Tuple[str, str]]) -> str:
    pending_list = list(pending)
    base_count = max(0, int(completed_count) - len(pending_list))
    digests = [
        _turn_digest(user_text, assistant_text)
        for user_text, assistant_text in pending_list
    ]
    payload = json.dumps(
        [base_count, int(completed_count), digests],
        ensure_ascii=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(
        _PENDING_DIGEST_PREFIX.encode() + payload.encode()
    ).hexdigest()


def _is_sha256_digest(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in _HEX_DIGITS for char in value)
    )


def _is_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _write_state(agent: Any, completed_count: int, pending_count: int) -> bool:
    path = _state_path(agent)
    if path is None:
        return False

    pending = list(getattr(agent, "_turn_bank_pending", ()) or ())
    checkpoint_turn = getattr(agent, "_turn_bank_last_completed_turn", None)
    if checkpoint_turn is None and pending:
        checkpoint_turn = pending[-1]
    if checkpoint_turn is None:
        checkpoint_turn = ("", "")
    completed = int(completed_count)
    payload = {
        "version": _STATE_VERSION,
        "completed_count": completed,
        "pending_count": int(len(pending)),
        "checkpoint_digest": _checkpoint_digest(
            completed, _turn_digest(*checkpoint_turn)
        ),
        "pending_digest": _pending_digest(completed, pending),
        "write_due": bool(getattr(agent, "_turn_bank_write_due", False)),
    }
    tmp_path: str | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=str(path.parent), prefix=f"{path.name}.", suffix=".tmp"
        )
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=True, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
        atomic_replace(tmp_path, path)
        tmp_path = None
        return True
    except Exception:
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        return False


def _legacy_full_history_turns(
    agent: Any, supplied: List[Tuple[str, str]], pending_count: int
) -> List[Tuple[str, str]]:
    if pending_count <= len(supplied):
        return supplied
    session_id = getattr(agent, "session_id", None)
    if not session_id:
        return supplied
    session_db = getattr(agent, "_session_db", None)
    if session_db is None:
        return supplied
    if getattr(session_db, "_conn", None) is not None:
        return _bounded_trailing_history_turns(
            session_db, session_id, supplied, pending_count
        )
    method = getattr(session_db, "get_messages_as_conversation", None)
    if method is None:
        return supplied
    try:
        full = completed_turns_from_messages(method(session_id))
    except Exception:
        return supplied
    return full if full else supplied


_TRAILING_WINDOW_MULTIPLIER = 6
_TRAILING_WINDOW_MAX_ROWS = 6_000
_CONTENT_JSON_PREFIX = "\x00json:"


def _bounded_trailing_history_turns(
    session_db: Any, session_id: str, supplied: List[Tuple[str, str]], pending_count: int
) -> List[Tuple[str, str]]:
    rows_needed = pending_count * 2 * _TRAILING_WINDOW_MULTIPLIER
    rows_needed = min(rows_needed, _TRAILING_WINDOW_MAX_ROWS)
    try:
        result = session_db._conn.execute(
            "SELECT role, content, tool_calls FROM messages "
            "WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, rows_needed),
        )
        rows = result.fetchall() or []
    except Exception:
        return supplied
    messages = []
    for row in reversed(rows):
        content = row["content"]
        if isinstance(content, str) and content.startswith(_CONTENT_JSON_PREFIX):
            try:
                content = json.loads(content[len(_CONTENT_JSON_PREFIX):])
            except (json.JSONDecodeError, TypeError):
                content = row["content"]
        message: Dict[str, Any] = {"role": row["role"], "content": content}
        if row["tool_calls"]:
            try:
                message["tool_calls"] = json.loads(row["tool_calls"])
            except (json.JSONDecodeError, TypeError):
                message["tool_calls"] = ""
        messages.append(message)
    try:
        full = completed_turns_from_messages(messages)
    except Exception:
        return supplied
    return full if full else supplied


def _legacy_persisted_end(
    turns: List[Tuple[str, str]], base: int, store: Any
) -> int:
    entries = getattr(store, "memory_entries", ())
    if not isinstance(entries, (list, tuple, set)):
        return base
    counts: Dict[str, int] = {}
    for entry in entries:
        if isinstance(entry, str):
            counts[entry] = counts.get(entry, 0) + 1
    formatted = [_format_turn(user, assistant) for user, assistant in turns]
    end = base
    for i in range(base, len(turns)):
        prior = sum(1 for k in range(i) if formatted[k] == formatted[i])
        if counts.get(formatted[i], 0) > prior:
            end = i + 1
        else:
            break
    return end


def _parent_branch_turns(agent: Any, parent_id: Any) -> List[Tuple[str, str]]:
    session_db = getattr(agent, "_session_db", None)
    if session_db is None:
        return []
    if getattr(session_db, "_conn", None) is not None:
        return _bounded_trailing_history_turns(
            session_db, parent_id, [], _TRAILING_WINDOW_MAX_ROWS
        )
    method = getattr(session_db, "get_messages_as_conversation", None)
    if method is None:
        return []
    try:
        full = completed_turns_from_messages(method(parent_id))
    except Exception:
        return []
    return full


def _strip_branch_copied_prefix(
    agent: Any, turns: List[Tuple[str, str]]
) -> Tuple[List[Tuple[str, str]], bool]:
    session_db = getattr(agent, "_session_db", None)
    session_id = getattr(agent, "session_id", None)
    parent_id = getattr(agent, "_parent_session_id", None)
    if not session_db or not session_id or not parent_id:
        return turns, False
    session_getter = getattr(session_db, "get_session", None)
    if session_getter is None:
        return turns, False
    try:
        parent = session_getter(parent_id) or {}
    except Exception:
        return turns, False
    if parent.get("end_reason") != "branched":
        return turns, False
    parent_turns = _parent_branch_turns(agent, parent_id)
    if not parent_turns:
        return turns, False
    max_k = min(len(turns), len(parent_turns))
    matches = [
        k
        for k in range(1, max_k + 1)
        if turns[:k] == parent_turns[len(parent_turns) - k :]
    ]
    if len(matches) > 1:
        return turns, True
    if not matches:
        return turns, False
    return list(turns[max(matches) :]), False


def hydrate_turn_bank(agent: Any, messages: Iterable[Dict[str, Any]]) -> None:
    """Restore the turn-bank counter and remainder for a fresh agent instance."""
    interval = parse_turn_bank_interval(getattr(agent, "_turn_bank_interval", 0))
    if (
        interval <= 0
        or not getattr(agent, "_memory_store", None)
        or getattr(agent, "_memory_enabled", True) is False
        or getattr(agent, "_turn_bank_completed_count", 0) != 0
        or getattr(agent, "_turn_bank_pending", None)
    ):
        return

    turns = completed_turns_from_messages(messages)
    turns, branch_blocked = _strip_branch_copied_prefix(agent, turns)
    if branch_blocked:
        agent._turn_bank_blocked = True
        agent._turn_bank_completed_count = len(turns)
        agent._turn_bank_pending = list(turns)
        return
    state = _read_lineage_state(agent)
    if state is _FUTURE_STATE_BARRIER:
        agent._turn_bank_blocked = True
        return
    if isinstance(state, dict):
        if state["version"] == _LEGACY_STATE_VERSION:
            _hydrate_legacy(agent, turns, state)
        else:
            _hydrate_version_two(agent, turns, state)
        return

    agent._turn_bank_completed_count = len(turns)
    persisted_end = _persisted_prefix_length(turns, interval, agent._memory_store)
    agent._turn_bank_pending = list(turns[persisted_end:])


def _hydrate_legacy(
    agent: Any, turns: List[Tuple[str, str]], state: Dict[str, Any]
) -> None:
    turns = _legacy_full_history_turns(agent, turns, state["pending_count"])
    if (
        len(turns) < state["completed_count"]
        or state["pending_count"] > len(turns)
    ):
        agent._turn_bank_blocked = True
        agent._turn_bank_completed_count = max(state["completed_count"], len(turns))
        agent._turn_bank_pending = list(turns)
        return
    agent._turn_bank_completed_count = max(state["completed_count"], len(turns))
    pending_base = max(0, state["completed_count"] - state["pending_count"])
    persisted_end = _legacy_persisted_end(turns, pending_base, agent._memory_store)
    agent._turn_bank_pending = list(turns[persisted_end:])


def _hydrate_version_two(
    agent: Any, turns: List[Tuple[str, str]], state: Dict[str, Any]
) -> None:
    completed_count = state["completed_count"]
    pending_count = state["pending_count"]
    turns = _legacy_full_history_turns(agent, turns, completed_count)
    checkpoint_index = completed_count - 1
    checkpoint_proved = (
        0 <= checkpoint_index < len(turns)
        and state["checkpoint_digest"]
        == _checkpoint_digest(
            completed_count, _turn_digest(*turns[checkpoint_index])
        )
    )
    proven_pending: List[Tuple[str, str]] | None = None
    recovered_tail: List[Tuple[str, str]] = []
    if checkpoint_proved:
        base = completed_count - pending_count
        pending = turns[base : base + pending_count]
        if (
            base >= 0
            and len(pending) == pending_count
            and state["pending_digest"] == _pending_digest(completed_count, pending)
        ):
            proven_pending = pending
            recovered_tail = turns[checkpoint_index + 1 :]
    if proven_pending is not None:
        candidate = list(proven_pending + recovered_tail)
    else:
        agent._turn_bank_blocked = True
        agent._turn_bank_completed_count = len(turns)
        agent._turn_bank_pending = list(turns)
        return
    interval = parse_turn_bank_interval(getattr(agent, "_turn_bank_interval", 0))
    persisted_end = _persisted_prefix_length(
        candidate,
        interval,
        agent._memory_store,
        base_count=completed_count - pending_count,
    )
    agent._turn_bank_completed_count = len(turns)
    agent._turn_bank_pending = list(candidate[persisted_end:])
    recovered_due = proven_pending is not None and bool(recovered_tail)
    agent._turn_bank_write_due = bool(state["write_due"]) or recovered_due


_TRUNCATION_MARKER = "...[truncated]..."


def _truncate_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    available = limit - len(_TRUNCATION_MARKER)
    head = available // 2
    tail = available - head
    return f"{text[:head]}{_TRUNCATION_MARKER}{text[-tail:]}"


def _format_turn(user_text: str, assistant_text: str) -> str:
    user = _truncate_text((user_text or "").strip(), _MAX_USER_CHARS)
    assistant = _truncate_text((assistant_text or "").strip(), _MAX_ASSISTANT_CHARS)
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
    return (
        isinstance(parsed, dict)
        and parsed.get("success") is True
        and parsed.get("staged", False) is False
    )


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


def _write_pending_turns(
    agent: Any,
    pending: List[Tuple[str, str]],
    completed_count: int,
    on_turn_persisted: Any = None,
) -> bool:
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

    for persisted_count, (user_text, assistant_text) in enumerate(pending, 1):
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
        if on_turn_persisted is not None:
            on_turn_persisted(persisted_count)
    return True


def _request_in_session_history(agent: Any, user_text: str) -> bool:
    messages = getattr(agent, "_session_messages", None) or []
    target = str(user_text or "").strip()
    return any(
        isinstance(message, dict)
        and message.get("role") == "user"
        and _message_text(message) == target
        for message in messages
    )


def _latest_request_unmatched(agent: Any, user_text: str) -> bool:
    messages = getattr(agent, "_session_messages", None) or []
    target = str(user_text or "").strip()
    last_index = None
    for index, message in enumerate(messages):
        if (
            isinstance(message, dict)
            and message.get("role") == "user"
            and _message_text(message) == target
        ):
            last_index = index
    if last_index is None:
        return False
    return not any(
        isinstance(message, dict) and message.get("role") == "assistant"
        for message in messages[last_index + 1 :]
    )


def _compression_continuation(agent: Any, old_id: Any, new_id: Any) -> bool:
    if not old_id or not new_id:
        return False
    if getattr(agent, "_parent_session_id", None) != old_id:
        return False
    session_db = getattr(agent, "_session_db", None)
    if session_db is None:
        return False
    return _valid_compression_parent(agent, session_db, new_id, old_id)


def _canonical_assistant_text(agent: Any, user_text: str) -> str | None:
    target = str(user_text or "").strip()
    if not target:
        return None
    messages = getattr(agent, "_session_messages", None) or []
    if not messages:
        return None
    try:
        turns = completed_turns_from_messages(messages)
    except Exception:
        return None
    for candidate_user, candidate_assistant in reversed(turns):
        if candidate_user == target:
            return candidate_assistant
    return None


def add_completed_turn(agent: Any, user_text: str, assistant_text: str) -> bool:
    """Retain a completed turn when the configured bank boundary is reached."""
    if getattr(agent, "_turn_bank_blocked", False):
        agent._turn_bank_pending = list(
            getattr(agent, "_turn_bank_pending", []) or []
        ) + [(str(user_text or ""), str(assistant_text or ""))]
        return False
    interval = parse_turn_bank_interval(getattr(agent, "_turn_bank_interval", 0))
    if (
        interval <= 0
        or not getattr(agent, "_memory_store", None)
        or getattr(agent, "_memory_enabled", True) is False
    ):
        return False
    if not str(assistant_text or "").strip() and _request_in_session_history(
        agent, user_text
    ):
        return False
    if _latest_request_unmatched(agent, user_text):
        return False

    canonical_assistant = _canonical_assistant_text(agent, user_text)
    if canonical_assistant is not None:
        assistant_text = canonical_assistant

    session_id = getattr(agent, "session_id", None)
    bound_session = getattr(agent, "_turn_bank_session_id", None)
    if bound_session != session_id and not _compression_continuation(
        agent, bound_session, session_id
    ):
        agent._turn_bank_completed_count = 0
        agent._turn_bank_pending = []
        agent._turn_bank_write_due = False
        agent._turn_bank_last_completed_turn = None
    agent._turn_bank_session_id = session_id

    existing_pending = list(getattr(agent, "_turn_bank_pending", []) or [])
    pending = existing_pending + [(str(user_text or ""), str(assistant_text or ""))]
    completed_count = int(getattr(agent, "_turn_bank_completed_count", 0)) + 1
    agent._turn_bank_completed_count = completed_count
    agent._turn_bank_last_completed_turn = pending[-1]
    retry_outstanding = bool(existing_pending) and (
        bool(getattr(agent, "_turn_bank_write_due", False))
        or (completed_count - 1) % interval == 0
    )
    if not retry_outstanding and completed_count % interval:
        agent._turn_bank_pending = pending
        agent._turn_bank_write_due = False
        _write_state(agent, completed_count, len(pending))
        return False

    agent._turn_bank_pending = pending
    agent._turn_bank_write_due = True
    _write_state(agent, completed_count, len(pending))

    def on_turn_persisted(persisted_count: int) -> None:
        agent._turn_bank_pending = pending[persisted_count:]
        _write_state(agent, completed_count, len(pending[persisted_count:]))

    if not _write_pending_turns(
        agent,
        pending,
        completed_count,
        on_turn_persisted=on_turn_persisted,
    ):
        return False

    agent._turn_bank_completed_count = completed_count
    agent._turn_bank_pending = []
    agent._turn_bank_write_due = False
    _write_state(agent, completed_count, 0)
    return True


__all__ = [
    "add_completed_turn",
    "completed_turns_from_messages",
    "hydrate_turn_bank",
    "parse_turn_bank_interval",
]
