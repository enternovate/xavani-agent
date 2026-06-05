# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Taste recall: turn learned style + preferences into generation context (L8).

``taste_context`` is what makes the agent *default to the learned way*: given a
brief, it deterministically selects the best-matching :class:`StyleProfile` and
renders a compact context block — the design direction, its key attributes, the
anti-generic ``avoid`` list, and the user's stated preferences — for injection
into a generation prompt. The agent then designs **originally** in that direction.

Selection is pure Python (R10); only the downstream generation uses the model.
"""

from __future__ import annotations

from xavani_learner.style_profile import StyleProfile, best_style, load_style_library


def taste_context(
    brief: str,
    library: list[StyleProfile] | None = None,
    preferences: list[str] | None = None,
) -> str:
    """Render the learned design direction + preferences for a brief."""
    lib = library if library is not None else load_style_library()
    profile = best_style(brief, lib)
    lines: list[str] = []
    if profile is not None:
        lines.append(f"Design direction: {profile.title} — {profile.inspiration}")
        for label, value in (
            ("layout", profile.layout),
            ("typography", profile.typography),
            ("color", profile.color),
            ("motion", profile.motion),
            ("whitespace", profile.whitespace),
            ("imagery", profile.imagery),
        ):
            if value:
                lines.append(f"  {label}: {value}")
        if profile.feel:
            lines.append(f"  feel: {', '.join(profile.feel)}")
        if profile.avoid:
            lines.append(f"  AVOID (anti-generic): {', '.join(profile.avoid)}")
    if preferences:
        lines.append("User preferences: " + "; ".join(preferences))
    lines.append(
        "Design ORIGINALLY in this direction — stay creative; never produce "
        "generic, template-y, or easily-identifiable output."
    )
    return "\n".join(lines)
