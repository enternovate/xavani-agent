# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Activity-line formatting: one line per action under a turn gutter.

Format: ``  ┊ 🔧 patch    cli.py  2.8s`` — icon, verb, optional target,
optional duration. Verbs are padded to a common width so targets align.
"""

from typing import Optional

GUTTER = "  ┊ "

_VERB_ICONS = {
    "patch": "🔧",
    "edit": "✏️",
    "terminal": "💻",
    "command": "💻",
    "search": "🔎",
    "read": "📖",
    "write": "✍️",
    "test": "🧪",
    "eval": "📊",
    "loop": "🔁",
    "review": "🔍",
    "plan": "🗂️",
}

_VERB_WIDTH = 9


def format_duration(seconds: float) -> str:
    if seconds < 0:
        return "0.0s"
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    rest = int(seconds % 60)
    return f"{minutes}m{rest:02d}s"


def activity(verb: str, target: str = "", *, seconds: Optional[float] = None,
             running: bool = False, note: str = "") -> str:
    """Render one activity line under the turn gutter."""
    icon = _VERB_ICONS.get(verb.lower(), "•")
    verb_cell = verb.ljust(_VERB_WIDTH)
    parts = [f"{GUTTER}{icon} {verb_cell}"]
    if target:
        parts.append(target)
    if seconds is not None:
        parts.append(format_duration(seconds))
    elif running:
        parts.append("…")
    line = " ".join(parts).rstrip()
    if note:
        line += f"  · {note}"
    return line


def detail(text: str) -> str:
    """A dim sub-line indented deeper than the activity gutter."""
    return f"{GUTTER}   {text}"


def banner_line(text: str, icon: str = "◆") -> str:
    """A top-level result line outside the gutter."""
    return f"{icon} {text}"
