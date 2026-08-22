# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Transcript export: session messages to markdown with metadata.

Reads the ``messages`` table of the Xavani state DB read-only and
renders one markdown file: a metadata header (session id, model,
started date, message count, tokens) followed by the conversation in
order. Connection injectable for offline tests.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

_QUERY = (
    "SELECT role, content, tool_name, timestamp FROM messages "
    "WHERE session_id = ? ORDER BY id"
)


def collect_messages(db_path: Path, session_id: str) -> List[Dict[str, Any]]:
    """Ordered user/assistant/tool messages for one session."""
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
    except sqlite3.Error:
        return []
    try:
        try:
            rows = conn.execute(_QUERY, (session_id,)).fetchall()
        except sqlite3.Error:
            return []
        out = []
        for row in rows:
            role = str(row["role"] or "")
            if role not in ("user", "assistant", "tool"):
                continue
            content = str(row["content"] or "").strip()
            if not content:
                continue
            entry: Dict[str, Any] = {
                "role": role,
                "content": content,
                "timestamp": row["timestamp"],
            }
            if row["tool_name"]:
                entry["tool_name"] = str(row["tool_name"])
            out.append(entry)
        return out
    finally:
        conn.close()


def render_export(
    session_id: str,
    messages: List[Dict[str, Any]],
    *,
    model: str = "",
    title: str = "",
) -> str:
    """Render the markdown transcript with a metadata header."""
    lines = [
        "---",
        f"session: {session_id}",
        f"title: {title or session_id}",
        f"model: {model or 'unknown'}",
        f"exported: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"messages: {len(messages)}",
        "---",
        "",
    ]
    for i, m in enumerate(messages, start=1):
        label = m["role"]
        if "tool_name" in m:
            label += f" ({m['tool_name']})"
        lines.append(f"## [{i}] {label}")
        lines.append("")
        lines.append(m["content"])
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def export_session(
    db_path: Path,
    session_id: str,
    out_dir: Path,
    *,
    model: str = "",
    title: str = "",
) -> Optional[Path]:
    """Export one session; returns the written path or None if empty."""
    messages = collect_messages(db_path, session_id)
    if not messages:
        return None
    out_dir.mkdir(parents=True, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id)
    target = out_dir / f"{safe}.md"
    target.write_text(
        render_export(session_id, messages, model=model, title=title),
        encoding="utf-8",
    )
    return target
