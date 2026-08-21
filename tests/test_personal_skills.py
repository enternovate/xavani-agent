# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.

"""Built-in personal category skills: personal-assistant."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
PERSONAL_DIR = REPO_ROOT / "oag_skills" / "personal"
MANIFEST_PATH = REPO_ROOT / "oag_skills" / "MANIFEST.json"
INDEX_PATH = REPO_ROOT / "website" / "static" / "api" / "skills-index.json"

PERSONAL_SKILLS = (
    "personal-assistant",
)


def _skill_md(name: str) -> Path:
    return PERSONAL_DIR / name / "SKILL.md"


def test_personal_skill_dirs_exist_with_skill_md():
    assert (PERSONAL_DIR / "DESCRIPTION.md").is_file()
    for name in PERSONAL_SKILLS:
        assert _skill_md(name).is_file(), f"missing {_skill_md(name)}"


def test_personal_frontmatter_parses_with_required_fields():
    for name in PERSONAL_SKILLS:
        meta = yaml.safe_load(
            _skill_md(name).read_text(encoding="utf-8").split("---")[1]
        )
        assert isinstance(meta, dict), name
        assert str(meta.get("name", "")).strip() == name
        assert str(meta.get("description", "")).strip(), name
        tags = meta["metadata"]["xavani"]["tags"]
        assert isinstance(tags, list) and tags, name


def test_manifest_lists_all_personal_entries():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    listed = {entry["name"] for entry in manifest["skills"]}
    for name in PERSONAL_SKILLS:
        assert name in listed, f"{name} missing from MANIFEST.json"


def test_skills_index_contains_built_in_personal_entries():
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    local = {
        entry["name"]
        for entry in index["skills"]
        if entry.get("source") == "oag-skills"
    }
    for name in PERSONAL_SKILLS:
        assert name in local, f"{name} missing from skills-index.json"


def test_personal_assistant_has_eval_rubric_with_six_criteria():
    text = _skill_md("personal-assistant").read_text(encoding="utf-8")
    assert "EVAL RUBRIC" in text
    rubric = text.split("EVAL RUBRIC", 1)[1]
    criteria = [line for line in rubric.splitlines() if line.startswith("| 1 |") or line.startswith("| 2 |") or line.startswith("| 3 |") or line.startswith("| 4 |") or line.startswith("| 5 |") or line.startswith("| 6 |")]
    assert len(criteria) == 6, f"expected 6 rubric criteria, found {len(criteria)}"
