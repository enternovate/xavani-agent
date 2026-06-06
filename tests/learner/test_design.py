# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the design-capabilities layer (v0.7.0 operator — distilled design craft)."""

from __future__ import annotations

from xavani_learner.design import design_brief
from xavani_learner.design_principles import design_principles_text, principles_for
from xavani_learner.design_review import design_review, design_score


# --- principles -------------------------------------------------------------

def test_principles_for_web_has_core_dimensions():
    p = principles_for("web")
    for key in ("layout", "typography", "color", "space", "accessibility", "hierarchy"):
        assert key in p


def test_poster_differs_from_web():
    assert principles_for("poster") != principles_for("web")


def test_unknown_medium_falls_back_to_default():
    assert principles_for("zzz-unknown") == principles_for("default")


def test_principles_text_mentions_craft():
    text = design_principles_text("deck").lower()
    assert "hierarchy" in text or "type" in text


# --- review (deterministic critique) ---------------------------------------

def test_design_review_flags_generic_and_low_contrast():
    findings = design_review("A hero with 3 cards, lorem ipsum, light gray text on white")
    assert findings
    assert any("contrast" in f.lower() for f in findings)


def test_crafted_spec_passes_review():
    spec = (
        "Asymmetric editorial grid, oversized variable display type, a single ink "
        "accent, generous whitespace, one clear focal point"
    )
    assert design_score(spec) == 0


# --- brief (taste + principles fused) --------------------------------------

def test_design_brief_fuses_taste_and_principles():
    brief = design_brief("a minimal premium SaaS landing page", "web")
    assert "Design direction" in brief          # learned taste
    assert "layout" in brief.lower()            # principles
    assert "avoid" in brief.lower()             # anti-generic guardrail


def test_design_brief_includes_preferences():
    brief = design_brief("a launch poster", "poster", preferences=["prefers bold type"])
    assert "bold type" in brief
