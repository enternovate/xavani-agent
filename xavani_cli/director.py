# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Director mode: drive worker sessions with read-only toolsets.

When enabled, every spawned subagent's toolset list is filtered down to
read-only toolsets — workers can look and reason but cannot mutate
files, run terminals, or send messages. Toggle per session with
/director on|off.
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import List

DIRECTOR_TOOLSETS = frozenset({
    "search", "web", "session_search", "vision", "video", "clarify",
})

_director_on: ContextVar[bool] = ContextVar("xavani_director", default=False)


def enable() -> None:
    _director_on.set(True)


def disable() -> None:
    _director_on.set(False)


def is_enabled() -> bool:
    return _director_on.get()


def director_filter_toolsets(toolsets: List[str]) -> List[str]:
    """Intersect a child's toolsets with the read-only set when enabled."""
    if not is_enabled():
        return toolsets
    return [t for t in toolsets if t in DIRECTOR_TOOLSETS]
