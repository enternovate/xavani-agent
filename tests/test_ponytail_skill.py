# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.

"""Built-in ponytail skill pack vendored from DietrichGebert/ponytail (MIT)."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
PONYTAIL_DIR = REPO_ROOT / "oag_skills" / "ponytail"
MANIFEST_PATH = REPO_ROOT / "oag_skills" / "MANIFEST.json"
INDEX_PATH = REPO_ROOT / "website" / "static" / "api" / "skills-index.json"

PONYTAIL_SKILLS = (
    "ponytail",
    "ponytail-audit",
    "ponytail-debt",
    "ponytail-gain",
    "ponytail-help",
    "ponytail-review",
)


def _skill_md(name: str) -> Path:
    if name == "ponytail":
        return PONYTAIL_DIR / "SKILL.md"
    return PONYTAIL_DIR / name / "SKILL.md"


def test_ponytail_skill_dirs_exist_with_skill_md():
    for name in PONYTAIL_SKILLS:
        assert _skill_md(name).is_file(), f"missing {_skill_md(name)}"


def test_ponytail_frontmatter_parses_with_required_fields():
    for name in PONYTAIL_SKILLS:
        meta = yaml.safe_load(
            _skill_md(name).read_text(encoding="utf-8").split("---")[1]
        )
        assert isinstance(meta, dict), name
        assert str(meta.get("name", "")).strip() == name
        assert str(meta.get("description", "")).strip(), name


def test_ponytail_attribution_preserves_upstream_license():
    attribution = (PONYTAIL_DIR / "ATTRIBUTION.md").read_text(encoding="utf-8")
    assert "DietrichGebert/ponytail" in attribution
    assert "MIT" in attribution


def test_manifest_lists_all_ponytail_entries():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    listed = {entry["name"] for entry in manifest["skills"]}
    for name in PONYTAIL_SKILLS:
        assert name in listed, f"{name} missing from MANIFEST.json"


def test_skills_index_contains_built_in_ponytail_entries():
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    local = {
        entry["name"]
        for entry in index["skills"]
        if entry.get("source") == "oag-skills"
    }
    for name in PONYTAIL_SKILLS:
        assert name in local, f"{name} missing from skills-index.json"
