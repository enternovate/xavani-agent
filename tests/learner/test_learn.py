# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for learn intake + preference capture (v0.7.0 operator L5–L7/L14)."""

from __future__ import annotations

from xavani_learner.preferences import PreferenceStore
from xavani_learner.style_learn import distill_profile, learn_file, learn_text, learn_url
from xavani_learner.style_profile import load_style_library
from xavani_operator.state import OperatorState


# --- L5: distillation (heuristic default + injectable LLM) ------------------

def test_distill_heuristic_derives_tags():
    p = distill_profile("minimal clean whitespace typography elegant restrained calm", "demo")
    assert p.name == "demo"
    assert p.tags          # keywords were derived
    assert p.inspiration   # attributed


def test_distill_with_injected_extractor():
    def extract(text):
        return {"title": "Custom", "tags": ["x"], "inspiration": "i", "avoid": ["generic"]}

    p = distill_profile("whatever", "demo", extract=extract)
    assert p.title == "Custom"
    assert p.tags == ["x"]


# --- L6: learn from text / file / url --------------------------------------

def test_learn_text_saves_loadable_profile(tmp_path):
    learn_text("bold immersive motion cinematic experimental", "demo", save_dir=tmp_path)
    assert (tmp_path / "demo.yaml").exists()
    assert any(x.name == "demo" for x in load_style_library(extra_dir=tmp_path))


def test_learn_file(tmp_path):
    ref = tmp_path / "ref.txt"
    ref.write_text("editorial typography reading longform magazine")
    p = learn_file(ref, save_dir=tmp_path)
    assert p.tags


def test_learn_url_uses_injected_fetch(tmp_path):
    p = learn_url(
        "https://example.com/cool-site",
        fetch=lambda url: "playful colorful brand vivid friendly",
        save_dir=tmp_path,
    )
    assert p.name
    assert p.tags
    assert "example.com" in p.inspiration  # attribution to the source


# --- L7/L14: preference capture (explicit + continuous) --------------------

def test_preference_record_and_recall(tmp_path):
    ps = PreferenceStore(OperatorState(root=tmp_path))
    ps.record("likes planning before building")
    ps.record_reference("https://lusion.co")
    recalled = ps.recall()
    assert any("planning" in t for t in recalled)
    assert any("lusion" in t for t in recalled)
    assert ps.list(kind="design_reference")
