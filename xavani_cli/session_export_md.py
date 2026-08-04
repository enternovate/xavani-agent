# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Render session exports as a readable Markdown transcript document.

Used by ``xavani sessions export --format md``.  Handles the dict shape
produced by ``SessionDB.export_session`` / ``export_all``: a session dict
with ``messages`` (each with ``role``, ``content``, ``timestamp``, and
optionally ``tool_calls`` / ``tool_name`` / ``finish_reason``).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List


def _content_text(content: Any) -> str:
    """Flatten message content (str or multimodal parts list) to text."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict):
                if part.get("type") == "image_url" or "image_url" in part:
                    parts.append("[image]")
                elif part.get("type") == "text" or "text" in part:
                    parts.append(str(part.get("text", "")))
                else:
                    parts.append(str(part))
            else:
                parts.append(str(part))
        return "\n".join(p for p in parts if p)
    return str(content)


def _fmt_ts(timestamp: Any) -> str:
    """Format a unix timestamp (float/str) as local ``YYYY-MM-DD HH:MM:SS``."""
    if timestamp in (None, ""):
        return ""
    try:
        return datetime.fromtimestamp(float(timestamp)).strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError, OSError, OverflowError):
        return str(timestamp)


def _tool_calls_summary(message: Dict[str, Any]) -> List[str]:
    """Summarize tool calls on a message into short ``name(args)`` strings."""
    summaries: List[str] = []
    calls = message.get("tool_calls") or []
    if isinstance(calls, str):
        calls = []
    for call in calls:
        if not isinstance(call, dict):
            continue
        raw_fn = call.get("function")
        fn: Dict[str, Any] = raw_fn if isinstance(raw_fn, dict) else {}
        name = fn.get("name") or call.get("name") or "?"
        arguments = fn.get("arguments") if fn.get("arguments") is not None else call.get("arguments")
        if arguments is None:
            arguments = ""
        if isinstance(arguments, dict):
            arguments = str(arguments)
        arguments = str(arguments).strip()
        if len(arguments) > 160:
            arguments = arguments[:160] + "…"
        summaries.append(f"{name}({arguments})" if arguments else name)
    if message.get("tool_name") and not summaries:
        summaries.append(str(message["tool_name"]))
    return summaries


def _message_markdown(message: Dict[str, Any]) -> str:
    role = str(message.get("role") or "unknown")
    ts = _fmt_ts(message.get("timestamp"))
    heading = f"### {role}"
    if ts:
        heading += f" — {ts}"
    finish = message.get("finish_reason")
    if finish:
        heading += f" *(finish: {finish})*"

    lines = [heading, ""]
    content = _content_text(message.get("content"))
    if content:
        lines.append(content)
        lines.append("")
    for summary in _tool_calls_summary(message):
        lines.append(f"- 🔧 `{summary}`")
    if message.get("reasoning"):
        reasoning = str(message["reasoning"]).strip()
        if reasoning:
            if len(reasoning) > 400:
                reasoning = reasoning[:400] + "…"
            lines.append(f"  - 💭 {reasoning}")
    if len(lines) > 2:
        lines.append("")
    return "\n".join(lines).rstrip()


def session_to_markdown(session: Dict[str, Any]) -> str:
    """Render one session dict as a Markdown transcript document."""
    return sessions_to_markdown([session])


def sessions_to_markdown(sessions: List[Dict[str, Any]]) -> str:
    """Render a list of session dicts as one Markdown transcript document."""
    sections: List[str] = []
    for session in sessions:
        session_id = str(session.get("id") or "?")
        title = str(session.get("title") or "Untitled session")
        lines = [f"# {title}", ""]
        meta = [f"- **Session**: `{session_id}`"]
        if session.get("source"):
            meta.append(f"- **Source**: {session['source']}")
        if session.get("created_at"):
            meta.append(f"- **Created**: {session['created_at']}")
        if session.get("last_active"):
            meta.append(f"- **Last active**: {session['last_active']}")
        messages = session.get("messages") or []
        meta.append(f"- **Messages**: {len(messages)}")
        lines.extend(meta)
        lines.append("")
        for message in messages:
            if isinstance(message, dict):
                lines.append(_message_markdown(message))
        sections.append("\n".join(lines).rstrip())

    return "\n\n---\n\n".join(sections) + "\n"
