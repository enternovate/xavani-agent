# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Render session exports as a readable HTML transcript document.

Used by ``xavani sessions export --format html``.  Handles the dict shape
produced by ``SessionDB.export_session`` / ``export_all``: a session dict
with ``messages`` (each with ``role``, ``content``, ``timestamp``, and
optionally ``tool_calls`` / ``tool_name`` / ``finish_reason``).
"""

from __future__ import annotations

import html
from datetime import datetime
from typing import Any, Dict, List

_STYLE = """
body { font-family: -apple-system, 'Segoe UI', Roboto, sans-serif;
       max-width: 860px; margin: 2rem auto; padding: 0 1rem;
       background: #fafafa; color: #222; }
h1 { font-size: 1.4rem; border-bottom: 2px solid #ddd; padding-bottom: .3rem; }
h2 { font-size: 1.15rem; margin-top: 2rem; }
.meta { color: #666; font-size: .85rem; margin: .3rem 0 1rem; }
.msg { background: #fff; border: 1px solid #e3e3e3; border-radius: 6px;
       padding: .6rem .8rem; margin: .6rem 0; }
.msg .head { font-size: .8rem; color: #888; margin-bottom: .3rem; }
.msg.user { border-left: 4px solid #2f80ed; }
.msg.assistant { border-left: 4px solid #27ae60; }
.msg.tool { border-left: 4px solid #f2c94c; background: #fffbea; }
.msg.system { border-left: 4px solid #9b51e0; }
.role { font-weight: 600; }
.content { white-space: pre-wrap; word-break: break-word; margin: .2rem 0; }
.toolcall { font-family: ui-monospace, Menlo, monospace; font-size: .85rem;
            background: #f4f4f4; border-radius: 4px; padding: .3rem .5rem;
            margin: .3rem 0; overflow-x: auto; }
.summary { color: #555; }
"""


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


def _message_html(message: Dict[str, Any]) -> str:
    role = str(message.get("role") or "unknown")
    ts = _fmt_ts(message.get("timestamp"))
    head = f'<span class="role">{html.escape(role)}</span>'
    if ts:
        head += f" · <span class='ts'>{html.escape(ts)}</span>"
    finish = message.get("finish_reason")
    if finish:
        head += f" · <span class='ts'>finish: {html.escape(str(finish))}</span>"

    body = ""
    content = _content_text(message.get("content"))
    if content:
        body += f'<div class="content">{html.escape(content)}</div>'
    for summary in _tool_calls_summary(message):
        body += f'<div class="toolcall">🔧 {html.escape(summary)}</div>'
    if message.get("reasoning"):
        reasoning = str(message["reasoning"]).strip()
        if reasoning:
            if len(reasoning) > 400:
                reasoning = reasoning[:400] + "…"
            body += (
                f'<div class="toolcall">💭 <span class="summary">'
                f"{html.escape(reasoning)}</span></div>"
            )

    css_role = role if role in ("user", "assistant", "tool", "system") else "unknown"
    return f'<div class="msg {css_role}"><div class="head">{head}</div>{body}</div>'


def session_to_html(session: Dict[str, Any]) -> str:
    """Render one session dict as a standalone HTML document."""
    return sessions_to_html([session])


def sessions_to_html(sessions: List[Dict[str, Any]]) -> str:
    """Render a list of session dicts as one HTML transcript document."""
    sections: List[str] = []
    for session in sessions:
        session_id = html.escape(str(session.get("id") or "?"))
        title = html.escape(str(session.get("title") or "Untitled session"))
        meta_bits = [f"id: {session_id}"]
        if session.get("source"):
            meta_bits.append(f"source: {html.escape(str(session['source']))}")
        if session.get("created_at"):
            meta_bits.append(f"created: {html.escape(str(session['created_at']))}")
        if session.get("last_active"):
            meta_bits.append(f"last active: {html.escape(str(session['last_active']))}")
        messages = session.get("messages") or []
        msg_html = "\n".join(
            _message_html(m) for m in messages if isinstance(m, dict)
        )
        sections.append(
            f"<h1>{title}</h1>\n"
            f'<div class="meta">{html.escape(" · ".join(meta_bits))}</div>\n'
            f"<p class='summary'>{len(messages)} message(s)</p>\n"
            f"{msg_html}"
        )

    return (
        "<!DOCTYPE html>\n<html>\n<head>\n"
        '<meta charset="utf-8">\n'
        "<title>Xavani session export</title>\n"
        f"<style>{_STYLE}</style>\n"
        "</head>\n<body>\n"
        + "\n".join(sections)
        + "\n</body>\n</html>\n"
    )
