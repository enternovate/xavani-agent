# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Xavani Oracle — consequence-conscious wisdom engine (v1.0.0 major ②).

A *conscience* for the agent: a curated memory of how exceptional people and
companies **rose** and how they **fell**, distilled into reusable patterns, plus
a deterministic projection of a decision's downstream **consequences**. The Oracle
lets the agent's advice avoid the small, repeated patterns that destroyed the
great (Solomon's overreach, leverage blowups, fraud, disruption-denial) while
borrowing what lifted them (focus, long horizons, margin of safety).

Spine (R10): everything here is **pure Python, zero model calls** — patterns are
matched and consequences are projected deterministically. Only ``research`` (a
later module) calls an LLM, and only to *distil* public playbooks into new
patterns. The soul/conscience values attach **append-only** via the
research-guidelines loader; the base identity is never rewritten (R7).

Public surface:
    WisdomPattern, load_corpus, match            -- patterns.py
    ConsequenceReport, project, detect_downfall   -- consequence.py
"""

from __future__ import annotations

from xavani_wisdom.consequence import (
    ConsequenceReport,
    detect_downfall,
    project,
)
from xavani_wisdom.patterns import (
    WisdomPattern,
    load_corpus,
    match,
)

__all__ = [
    "WisdomPattern",
    "load_corpus",
    "match",
    "ConsequenceReport",
    "project",
    "detect_downfall",
]
