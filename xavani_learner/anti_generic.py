# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Anti-generic design guardrail (v0.7.0 operator L4).

The user's brief is explicit: stay **away from generic, template-y,
easily-identifiable** designs. This module deterministically flags the tell-tale
signs of generic output (placeholder copy, default framework looks, the cliché
"hero + 3 cards", system fonts, black-on-white-only) and checks output against a
chosen :class:`StyleProfile`'s ``avoid`` list. It does **not** replace the agent's
creativity — it's a tripwire that says "this looks generic, push further".

Pure Python, **no LLM** (R10).
"""

from __future__ import annotations

import re

_GENERIC_SIGNALS: list[tuple[str, str]] = [
    (r"lorem ipsum", "placeholder lorem-ipsum copy"),
    (r"\bbootstrap\b", "default Bootstrap look"),
    (r"default tailwind|tailwind default|untouched tailwind", "default Tailwind look"),
    (r"hero.{0,40}\b(three|3)\b\s+\w*\s*cards|\b(three|3)\s+feature cards", "cliché hero + 3-cards layout"),
    (r"\b3[- ]column cards|three[- ]column cards|generic card grid", "generic card grid"),
    (r"powered by|made with love|free template|website template", "template boilerplate"),
    (r"feature\s*1\b.*feature\s*2\b|placeholder (text|content)", "placeholder content"),
    (r"black text on white only|only black and white|#000 on #fff only", "default black-on-white-only palette"),
    (r"\b(arial|times new roman|helvetica only)\b", "system default fonts"),
    (r"generic|cookie[- ]cutter|looks like every other", "self-described generic"),
]


def flag_generic(text: str) -> list[str]:
    """Return findings for template-y / generic signals in ``text``."""
    low = text.lower()
    return [msg for pattern, msg in _GENERIC_SIGNALS if re.search(pattern, low)]


def is_generic(text: str, threshold: int = 1) -> bool:
    """True if ``text`` trips at least ``threshold`` generic signals."""
    return len(flag_generic(text)) >= threshold


def flag_against_profile(text: str, profile) -> list[str]:
    """Return ``avoid:`` findings where ``text`` hits the profile's anti-patterns."""
    low = text.lower()
    return [f"avoid: {a}" for a in getattr(profile, "avoid", []) if a and a.lower() in low]
