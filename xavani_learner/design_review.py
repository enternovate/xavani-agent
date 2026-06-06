# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""High-level design critique (v0.7.0 operator — design craft).

A deterministic review of a design (a spec, description, or markup string) against
the craft fundamentals: it folds in the anti-generic guardrail and adds checks a
good designer would flag — low contrast (accessibility), type too small, and too
many fonts. So the agent can **review its own designs** and push for higher craft.
Pure Python, no LLM (R10).
"""

from __future__ import annotations

import re

from xavani_learner.anti_generic import flag_generic

_REVIEW: list[tuple[str, str]] = [
    (r"(light\s+)?gr[ae]y\b[^.]*\bon\s+white|#c{2,}\b[^.;]*#f{3,}",
     "low contrast (gray on white) — fails WCAG AA accessibility"),
    (r"\b1[0-2]px\b[^.;]*\b(body|paragraph|text)\b|tiny\s+(text|type)",
     "body type too small to read comfortably"),
    (r"font-family[^;]*,[^;]*,[^;]*,",
     "too many fonts — pick one display + one text family"),
]


def design_review(spec: str) -> list[str]:
    """Return craft findings for a design spec/description (empty = passes)."""
    low = (spec or "").lower()
    findings = list(flag_generic(spec))
    for pattern, message in _REVIEW:
        if re.search(pattern, low):
            findings.append(message)
    return list(dict.fromkeys(findings))


def design_score(spec: str) -> int:
    """Number of craft issues (0 = clean)."""
    return len(design_review(spec))
