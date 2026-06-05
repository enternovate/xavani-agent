# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for design style profiles + selector (v0.7.0 operator L1–L3/L11/L12)."""

from __future__ import annotations

from xavani_learner.style_profile import (
    StyleProfile,
    best_style,
    load_style_library,
    select_styles,
)


def test_profile_round_trips_through_dict():
    p = StyleProfile(name="x", title="X", inspiration="insp", tags=["minimal"], feel=["calm"])
    restored = StyleProfile.from_dict(p.to_dict())
    assert restored.name == "x"
    assert restored.tags == ["minimal"]
    assert restored.feel == ["calm"]


def test_seed_library_is_curated_and_attributed():
    lib = load_style_library()
    assert len(lib) >= 6                       # a real curated set
    assert all(p.inspiration for p in lib)     # L12: every profile attributes inspiration
    assert all(p.avoid for p in lib)           # every profile says what to avoid (anti-generic)
    assert len({p.name for p in lib}) == len(lib)  # unique names


def test_select_ranks_minimal_brief_to_clarity():
    lib = load_style_library()
    ranked = select_styles("a minimal, calm SaaS landing page with lots of whitespace", lib)
    assert ranked
    top = ranked[0][0]
    assert any(t in {"minimal", "clarity", "saas", "whitespace", "calm"} for t in top.tags)


def test_select_ranks_editorial_brief_to_editorial():
    lib = load_style_library()
    top = select_styles("editorial typography-led longform reading experience", lib)[0][0]
    assert "editorial" in top.tags


def test_select_is_deterministic():
    lib = load_style_library()
    a = [p.name for p, _ in select_styles("playful colorful brand site", lib)]
    b = [p.name for p, _ in select_styles("playful colorful brand site", lib)]
    assert a == b


def test_best_style_returns_profile_or_none():
    lib = load_style_library()
    assert best_style("immersive cinematic motion agency portfolio", lib) is not None
    assert best_style("anything", []) is None


def test_user_profiles_extend_seed(tmp_path):
    extra = tmp_path / "style_library"
    extra.mkdir()
    (extra / "custom.yaml").write_text(
        "name: custom\ntitle: Custom\ninspiration: mine\ntags: [unique-tag]\navoid: [generic]\n"
    )
    lib = load_style_library(extra_dir=extra)
    assert any(p.name == "custom" for p in lib)
    assert best_style("unique-tag please", lib).name == "custom"
