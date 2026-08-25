# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Fuzzy matching for slash commands.

Scores an input against candidate names: exact > prefix > substring >
subsequence, with shorter targets winning ties. Powers unknown-command
suggestions.
"""

from __future__ import annotations


def score(query: str, target: str) -> int:
    """Score ``query`` against ``target`` (0 = no match, 100 = exact)."""
    if not query or not target:
        return 0
    q = query.lower()
    t = target.lower()
    if q == t:
        return 100
    if t.startswith(q):
        # Tighter (shorter) targets score higher as prefixes.
        return 90 - min(len(t) - len(q), 20)
    idx = t.find(q)
    if idx != -1:
        return 70 - min(idx, 10) - min(len(t), 10)
    # Subsequence check: all query chars appear in order in target.
    pos = 0
    for ch in q:
        pos = t.find(ch, pos)
        if pos == -1:
            return 0
        pos += 1
    return 40 - min(len(t), 15)


def best_match(query: str, candidates: list[str]) -> str | None:
    """Return the highest-scoring candidate, or None when nothing scores."""
    if not query or not candidates:
        return None
    best_name = None
    best_score = 0
    for name in sorted(candidates):
        s = score(query, name)
        if s > best_score:
            best_score = s
            best_name = name
    return best_name
