# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Design brief — fuse learned taste + high-level principles (v0.7.0 operator).

``design_brief`` is what makes the agent design *at a high level, in your style*:
it combines the deterministically-selected :class:`StyleProfile` (learned taste)
+ stated preferences with the medium-appropriate design **principles**, into one
block injected into generation. Selection + principles are pure Python (R10);
only the downstream generation uses the model. The build/promote workstreams call
this for any design work (sites, posters, decks).
"""

from __future__ import annotations

from xavani_learner.design_principles import design_principles_text
from xavani_learner.taste import taste_context


def design_brief(
    brief: str,
    medium: str = "web",
    library: list | None = None,
    preferences: list[str] | None = None,
) -> str:
    """Return a high-level design brief: learned taste + principles for the medium."""
    taste = taste_context(brief, library=library, preferences=preferences)
    return f"{taste}\n\nDesign principles ({medium}):\n{design_principles_text(medium)}"
