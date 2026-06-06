# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""High-level design principles, per medium (v0.7.0 operator — design craft).

The *craft* distilled from the discipline behind Claude's canvas-design /
frontend-design / pptx skills — layout, typography, colour, space, hierarchy,
focal point, motion, accessibility — expressed as structured, deterministic
guidance for each medium (web, poster, deck, ui, brand). These are principles, not
copies: they tell the agent *how to design well*, which it then applies in the
learned taste. Pure data, no LLM (R10).
"""

from __future__ import annotations

_PRINCIPLES: dict[str, dict[str, str]] = {
    "web": {
        "layout": "clear grid, strong above-the-fold focal point, generous whitespace, intentional rhythm",
        "typography": "confident type scale (3-5 steps), one display + one text family, comfortable measure (60-75ch)",
        "color": "restrained palette (1-2 brand + neutrals), one accent; text contrast >= 4.5:1",
        "space": "an 8pt spacing system; whitespace as structure, not filler",
        "hierarchy": "one primary action per view; size/weight/colour guide the eye",
        "focal": "a single hero idea, not a wall of equal blocks",
        "motion": "purposeful scroll reveals + micro-interactions; never decoration",
        "accessibility": "WCAG AA contrast, visible focus states, semantic structure, reduced-motion respect",
        "avoid": "generic hero+3-cards, stock photos, default framework spacing, low-contrast gray",
    },
    "poster": {
        "layout": "ONE focal point, bold composition, edge-to-edge or strong deliberate margins",
        "typography": "oversized display type as the hero; tight and expressive",
        "color": "high-impact, limited palette; strong figure/ground contrast",
        "space": "dramatic negative space framing the single message",
        "hierarchy": "title > subject > detail; readable at a glance and from a distance",
        "focal": "the single message/image dominates the canvas",
        "motion": "static — composition itself must carry the energy",
        "accessibility": "legible at distance; high contrast",
        "avoid": "clutter, many competing elements, tiny type, safe centred layouts",
    },
    "deck": {
        "layout": "one idea per slide, disciplined grid, consistent alignment across slides",
        "typography": "clear scale (title/heading/body), generous line-height, limited families",
        "color": "restrained, consistent theme; accessible contrast on every slide",
        "space": "generous; whitespace is focus, never bullet walls",
        "hierarchy": "one takeaway per slide, supported not buried",
        "focal": "one chart/visual/idea per slide",
        "motion": "minimal, purposeful transitions",
        "accessibility": "high contrast, large legible type, alt text for visuals",
        "avoid": "dense bullet walls, clashing fonts, clip-art, low contrast",
    },
    "ui": {
        "layout": "consistent grid + spacing tokens, sensible density, an obvious primary action",
        "typography": "legible UI scale, tabular figures for data, strong label/value hierarchy",
        "color": "neutral base + semantic colours (success/warn/error), accessible interaction states",
        "space": "a consistent spacing scale; group related, separate unrelated (proximity)",
        "hierarchy": "primary > secondary > tertiary actions; one clear default",
        "focal": "the user's current task is unmistakable",
        "motion": "fast, informative feedback; respect reduced-motion",
        "accessibility": "AA contrast, focus rings, keyboard nav, hit targets >= 44px",
        "avoid": "decorative chrome, inconsistent spacing, ambiguous primary action",
    },
    "brand": {
        "layout": "a coherent system (logo, grid, spacing) applied consistently across touchpoints",
        "typography": "a distinctive, ownable type pairing",
        "color": "a memorable, restrained palette with clear roles",
        "space": "consistent rhythm everywhere",
        "hierarchy": "consistent voice and visual emphasis",
        "focal": "one clear brand idea / feeling",
        "motion": "a signature, consistent motion language",
        "accessibility": "the system holds AA contrast everywhere",
        "avoid": "trend-chasing, inconsistency, generic stock identity",
    },
}

# Unknown / "default" medium → web principles (the sensible general case).
_DEFAULT = _PRINCIPLES["web"]
_ORDER = ["layout", "typography", "color", "space", "hierarchy", "focal", "motion", "accessibility", "avoid"]


def principles_for(medium: str) -> dict[str, str]:
    """Return the high-level design principles for ``medium`` (web/poster/deck/ui/brand)."""
    return _PRINCIPLES.get((medium or "").lower(), _DEFAULT)


def design_principles_text(medium: str) -> str:
    """Render the principles for ``medium`` as a generation-ready block."""
    p = principles_for(medium)
    return "\n".join(f"{key}: {p[key]}" for key in _ORDER if key in p)
