# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.

"""Built-in web-development category skill: anti-slop."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WEBDEV_DIR = REPO_ROOT / "oag_skills" / "web-development"
MANIFEST_PATH = REPO_ROOT / "oag_skills" / "MANIFEST.json"
INDEX_PATH = REPO_ROOT / "website" / "static" / "api" / "skills-index.json"

WEBDEV_SKILLS = (
    "anti-slop",
)

# Rule names verified against the upstream dmmulroy/anti-slop README.
VERIFIED_RULES = (
    "no-chained-type-assertions",
    "no-module-mocking",
    "no-widen-then-assert",
    "require-safety-comment-for-type-assertion",
)

ATTRIBUTION_LINK = "https://github.com/dmmulroy/anti-slop"


def _skill_md(name: str) -> Path:
    return WEBDEV_DIR / name / "SKILL.md"


def test_webdev_skill_dirs_exist_with_skill_md():
    assert (WEBDEV_DIR / "DESCRIPTION.md").is_file()
    for name in WEBDEV_SKILLS:
        assert _skill_md(name).is_file(), f"missing {_skill_md(name)}"


def test_antislop_frontmatter_parses_with_required_fields():
    meta = yaml.safe_load(
        _skill_md("anti-slop").read_text(encoding="utf-8").split("---")[1]
    )
    assert isinstance(meta, dict)
    assert str(meta.get("name", "")).strip() == "anti-slop"
    assert str(meta.get("description", "")).strip()
    tags = meta["metadata"]["xavani"]["tags"]
    assert isinstance(tags, list) and tags


def test_manifest_lists_antislop_under_web_development():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    entries = {
        entry["name"]: entry.get("category")
        for entry in manifest["skills"]
    }
    assert "anti-slop" in entries
    assert entries["anti-slop"] == "web-development"


def test_skills_index_contains_antislop_under_web_development():
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    local = {
        entry["name"]: entry
        for entry in index["skills"]
        if entry.get("source") == "oag-skills"
    }
    assert "anti-slop" in local
    assert local["anti-slop"].get("extra", {}).get("category") == "web-development"


def test_antislop_content_covers_rules_wiring_and_attribution():
    text = _skill_md("anti-slop").read_text(encoding="utf-8")
    assert "oxlint" in text.lower()
    for rule in VERIFIED_RULES:
        assert rule in text, f"anti-slop missing upstream rule '{rule}'"
    assert ATTRIBUTION_LINK in text
    assert "MIT" in text
    assert "Python" in text, "scope guard must state it never applies to Python"
