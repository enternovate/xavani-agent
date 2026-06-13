# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Self-faults — turn the agent's/user's own errors into watch-patterns (v1.0.0 ②).

The user's vision: *"the agent should also be learning from its faults, its
patterns, then maximise its output."* This reads the daily **error log** (from the
8pm ritual) and, when an assumption/belief recurs, distils a **personalised
downfall pattern** the Oracle's detector then watches for — so a mistake made
twice is flagged the third time.

Pure Python, deterministic, zero model calls (R10).
"""

from __future__ import annotations

import re
from collections import Counter

from xavani_wisdom.patterns import _STOP, WisdomPattern


def _terms(text: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9]+", str(text).lower()) if len(t) > 3 and t not in _STOP]


def _entry_texts(entry: dict) -> list[str]:
    """Pull the assumption/belief/prediction text out of one error-log entry dict."""
    out: list[str] = []
    for item in entry.get("wasted_effort", []) or []:
        out.append(str(item.get("assumption", "")))
    for item in entry.get("beliefs_revised", []) or []:
        out.append(str(item.get("believed", "")))
    for item in entry.get("predictions_missed", []) or []:
        out.append(str(item.get("predicted", "")))
    return [t for t in out if t.strip()]


def learn_from_errors(entries: list[dict], *, min_repeats: int = 2) -> list[WisdomPattern]:
    """Distil recurring mistakes into personalised downfall patterns. Deterministic.

    A term that shows up as a wrong assumption/belief on ``min_repeats`` or more
    distinct days becomes a watch-pattern. Returns patterns sorted by id.
    """
    # Count the *distinct days* each term appears as a fault (so one rambling day
    # doesn't manufacture a pattern).
    day_term_sets: list[set[str]] = []
    for entry in entries:
        terms: set[str] = set()
        for text in _entry_texts(entry):
            terms.update(_terms(text))
        if terms:
            day_term_sets.append(terms)

    counts: Counter[str] = Counter()
    for terms in day_term_sets:
        counts.update(terms)

    patterns: list[WisdomPattern] = []
    for term, n in counts.items():
        if n < min_repeats:
            continue
        patterns.append(
            WisdomPattern(
                id=f"self-fault-{term}",
                kind="downfall",
                figure="(your own recurring pattern)",
                domain="self",
                era="learned",
                what_they_did=f"A wrong assumption/belief involving '{term}' recurred on {n} days.",
                the_signal=[f"you have been off about '{term}' before"],
                the_lesson=(
                    f"You've misjudged '{term}' repeatedly — slow down and check it explicitly "
                    f"next time instead of trusting the same assumption."
                ),
                signals=["self_fault", f"repeat_{term}"],
                keywords=[term],
                sources=["your own 8pm error log"],
            )
        )
    patterns.sort(key=lambda p: p.id)
    return patterns
