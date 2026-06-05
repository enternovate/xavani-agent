# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the anti-generic guardrail + taste recall (v0.7.0 operator L4/L8)."""

from __future__ import annotations

from xavani_learner.anti_generic import flag_against_profile, flag_generic, is_generic
from xavani_learner.style_profile import StyleProfile
from xavani_learner.taste import taste_context


# --- L4: anti-generic guardrail --------------------------------------------

def test_flag_generic_catches_template_signals():
    findings = flag_generic("A hero section with 3 cards, lorem ipsum, built with Bootstrap")
    assert findings
    assert any("lorem" in f.lower() for f in findings)


def test_distinctive_description_is_not_generic():
    text = "An asymmetric editorial grid with oversized variable type and a single ink accent"
    assert is_generic(text) is False


def test_flag_against_profile_uses_avoid_list():
    p = StyleProfile(name="x", avoid=["stock photos"])
    assert flag_against_profile("a page full of stock photos", p)
    assert flag_against_profile("custom illustration only", p) == []


# --- L8: taste recall -------------------------------------------------------

def test_taste_context_selects_direction_and_warns_against_generic():
    ctx = taste_context("a minimal calm SaaS page with lots of whitespace")
    assert "clarity" in ctx.lower()        # picked the clarity-precision direction
    assert "avoid" in ctx.lower()          # carries the anti-generic guardrail
    assert "creativ" in ctx.lower()        # tells the agent to stay creative


def test_taste_context_includes_preferences():
    ctx = taste_context("editorial typography", preferences=["likes planning", "prefers dark themes"])
    assert "planning" in ctx


def test_taste_context_can_select_claude_craft_for_decks():
    ctx = taste_context("a polished slide deck / pptx presentation with clear hierarchy")
    assert "claude" in ctx.lower() or "craft" in ctx.lower()
