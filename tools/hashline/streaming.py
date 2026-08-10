"""Streaming edit preview for hashline (Task 18, ported from omp's streaming.ts).

While the model is still authoring a hashline payload, the edit tool wants a
best-effort preview of what will land — without ever mutating the snapshot
store.  This module provides the two pieces of that preview:

* :func:`preview_parse` — parse a PARTIAL payload strictly, and when the
  strict parser rejects it, progressively trim trailing lines (up to
  :data:`MAX_TRAILING_TRIM`) and retry.  A prefix that parses cleanly with
  at least one complete section wins: the dropped trailing rows are the
  in-flight tail of the stream.  Never raises.
* :func:`diff_sections` — read-only per-section preview against a
  :class:`~tools.hashline.snapshots.SnapshotStore`.  Each section's base is
  resolved via ``store.get`` and its ops are dry-run in memory on a copy
  (reusing the apply engine's ``_simulate_section``, which performs no
  writes); the store is never recorded to or invalidated.  Each entry
  reports the action (``edit`` / ``remove`` / ``move`` / ``noop`` /
  ``error``), before/after line counts, and the first
  :data:`PREVIEW_CHANGED_LINES` unified-diff rows.

Mirrors omp's streaming strategy: errors in one section never wipe the
previews of the sections before it (per-section ``error`` entries), and the
preview register state is local to the call, so no session state leaks.
"""

from __future__ import annotations

import difflib
from typing import Dict, List, Optional, Tuple, Union, cast

from .apply import ApplyError, _simulate_section
from .guard import NoopGuard
from .parser import ParseError, parse
from .snapshots import SnapshotStore

__all__ = ["MAX_TRAILING_TRIM", "PREVIEW_CHANGED_LINES", "diff_sections", "preview_parse"]

#: How many trailing lines to trim while hunting for a parseable prefix.
MAX_TRAILING_TRIM = 5
#: How many unified-diff rows a preview entry carries per file.
PREVIEW_CHANGED_LINES = 8


def preview_parse(text: str) -> dict:
    """Best-effort parse of a PARTIAL hashline payload. Never raises.

    Returns ``{"complete": bool, "sections": list, "error": str | None}``.
    The full payload is parsed strictly first; on :class:`ParseError`,
    trailing lines are trimmed one at a time (up to
    :data:`MAX_TRAILING_TRIM`) and the prefix re-parsed.  The first trim
    that parses cleanly with at least one complete section wins —
    ``complete=True`` with those sections (the dropped rows are the
    in-flight tail).  If no trim recovers a parse, ``complete=False`` with
    the ORIGINAL error text.
    """
    try:
        sections = parse(text)
    except ParseError as exc:
        original_error = exc.message
        lines = text.split("\n")
        for trim in range(1, MAX_TRAILING_TRIM + 1):
            if len(lines) <= trim:
                break
            candidate = "\n".join(lines[:-trim])
            try:
                sections = parse(candidate)
            except ParseError:
                continue
            if sections:  # parse() never returns empty, but stay defensive
                return {"complete": True, "sections": sections, "error": None}
        return {"complete": False, "sections": [], "error": original_error}
    except TypeError as exc:  # non-str payloads
        return {"complete": False, "sections": [], "error": str(exc)}
    return {"complete": True, "sections": sections, "error": None}


def _split_lines(text: str) -> List[str]:
    """Line list matching the apply engine's split (trailing newline ignored)."""
    if text == "":
        return []
    lines = text.split("\n")
    if lines and lines[-1] == "" and text.endswith("\n"):
        lines = lines[:-1]
    return lines


def _first_changed_lines(
    base_text: str, result_text: str, limit: int = PREVIEW_CHANGED_LINES
) -> List[str]:
    """First ``limit`` unified-diff rows between base and result (no headers)."""
    base_lines = _split_lines(base_text)
    result_lines = _split_lines(result_text)
    if base_lines == result_lines:
        return []
    diff = list(difflib.unified_diff(base_lines, result_lines, lineterm=""))
    body = diff[2:] if len(diff) >= 2 else diff  # drop '--- ' / '+++ ' headers
    return body[:limit]


def diff_sections(store: SnapshotStore, sections: list) -> List[dict]:
    """Read-only per-section preview against ``store``. Never modifies it.

    Each section's base snapshot is resolved via ``store.get`` and its ops
    are dry-run in memory on a copy (the apply engine's ``_simulate_section``
    — no writes, no recording).  Returns one entry per section in order:

    ``{path, action, base_lines, result_lines, changed_lines, error}`` where
    ``action`` is ``"edit"`` / ``"remove"`` / ``"move"`` / ``"noop"`` /
    ``"error"``; ``changed_lines`` holds the first
    :data:`PREVIEW_CHANGED_LINES` unified-diff rows (empty for ``remove`` /
    ``noop``); a ``move`` entry also carries ``dest``.  Registers persist
    across sections in patch order (matching apply), but the register state
    is local to this call.
    """
    previews: List[dict] = []
    state: Dict[str, object] = {"anon": None, "named": {}}
    guard = NoopGuard()

    for sec in sections:
        entry: dict = {
            "path": sec.path,
            "action": "error",
            "base_lines": 0,
            "result_lines": 0,
            "changed_lines": [],
            "error": None,
        }
        base = store.get(sec.path)
        if base is None:
            entry["error"] = (
                f"[{sec.path}#{sec.tag}]: no snapshot recorded for this path — "
                "read the file first"
            )
            previews.append(entry)
            continue
        try:
            base_text = base.content.decode("utf-8")
        except UnicodeDecodeError:
            entry["error"] = f"[{sec.path}#{base.tag}]: snapshot is not valid UTF-8"
            previews.append(entry)
            continue
        entry["base_lines"] = len(_split_lines(base_text))
        try:
            action, value = _simulate_section(sec, base, state, guard=guard)
        except ApplyError as exc:
            entry["error"] = str(exc)
            previews.append(entry)
            continue
        if action == "edit":
            entry["action"] = "edit"
            entry["result_lines"] = len(_split_lines(cast(str, value)))
            entry["changed_lines"] = _first_changed_lines(base_text, cast(str, value))
        elif action == "remove":
            entry["action"] = "remove"
            entry["result_lines"] = 0
        elif action == "move":
            dest, content = cast(Tuple[str, str], value)
            entry["action"] = "move"
            entry["dest"] = dest
            entry["result_lines"] = len(_split_lines(content))
            entry["changed_lines"] = _first_changed_lines(base_text, content)
        else:  # "noop" — guard-suppressed byte-identical edit
            entry["action"] = "noop"
            entry["result_lines"] = entry["base_lines"]
        previews.append(entry)
    return previews
