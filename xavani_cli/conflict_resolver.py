# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Git merge-conflict parsing and one-marker resolution.

Conflicts are numbered from 1 in file order. Strategies pick a side per
conflict or for every conflict at once: ``ours``, ``theirs``, or ``base``
(diff3 style; falls back to ``ours`` content when no base section exists).
"""

import re

_START_RE = re.compile(r"^<{7}.*$", re.MULTILINE)
_SEP_RE = re.compile(r"^\|{7}.*$", re.MULTILINE)
_EQUALS_RE = re.compile(r"^={7}\s*$")
_END_RE = re.compile(r"^>{7}.*$", re.MULTILINE)
_STRATEGIES = ("ours", "theirs", "base")


def parse_conflicts(text: str) -> list:
    """Return conflicts as dicts: index, start/end line offsets, sides."""
    conflicts = []
    lines = text.splitlines(keepends=True)
    i = 0
    while i < len(lines):
        if not _START_RE.match(lines[i]):
            i += 1
            continue
        start = i
        ours, base, theirs = [], [], []
        section = "ours"
        end_found = False
        i += 1
        while i < len(lines):
            line = lines[i]
            if _SEP_RE.match(line):
                section = "base"
                i += 1
                continue
            if _EQUALS_RE.match(line):
                section = "theirs"
                i += 1
                continue
            if _START_RE.match(line):
                break
            if _END_RE.match(line):
                end_found = True
                i += 1
                break
            {"ours": ours, "base": base, "theirs": theirs}[section].append(line)
            i += 1
        if not end_found:
            break
        conflicts.append({
            "index": len(conflicts) + 1,
            "start_line": start,
            "end_line": i,
            "ours": "".join(ours),
            "theirs": "".join(theirs),
            "base": "".join(base),
        })
    return conflicts


def _chosen_side(conflict: dict, strategy: str) -> str:
    if strategy == "ours":
        return conflict["ours"]
    if strategy == "theirs":
        return conflict["theirs"]
    return conflict["base"] or conflict["ours"]


def resolve_conflicts(text: str, strategy: str) -> str:
    """Resolve every conflict in ``text`` with ``strategy``."""
    if strategy not in _STRATEGIES:
        raise ValueError(f"unknown strategy {strategy!r}: expected ours/theirs/base")
    lines = text.splitlines(keepends=True)
    out = []
    i = 0
    n = len(lines)
    while i < n:
        if not _START_RE.match(lines[i]):
            out.append(lines[i])
            i += 1
            continue
        block_start = i
        depth = 0
        j = i
        end_j = None
        while j < n:
            if _START_RE.match(lines[j]):
                depth += 1
            elif _END_RE.match(lines[j]):
                depth -= 1
                if depth == 0:
                    end_j = j
                    break
            j += 1
        if end_j is None:
            out.extend(lines[block_start:])
            break
        segment = "".join(lines[block_start:end_j + 1])
        conflicts = parse_conflicts(segment)
        replacement = "".join(
            _chosen_side(c, strategy) for c in conflicts
        ) if conflicts else ""
        out.append(replacement)
        i = end_j + 1
    return "".join(out)


def count_conflicts(text: str) -> int:
    """Number of top-level conflict blocks."""
    depth = 0
    count = 0
    for line in text.splitlines(keepends=True):
        if _START_RE.match(line):
            depth += 1
        elif _END_RE.match(line) and depth > 0:
            if depth == 1:
                count += 1
            depth -= 1
    return count
