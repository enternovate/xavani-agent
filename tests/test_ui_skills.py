# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.

"""Built-in UI category skills: ai-native-ui."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
UI_DIR = REPO_ROOT / "oag_skills" / "ui"
MANIFEST_PATH = REPO_ROOT / "oag_skills" / "MANIFEST.json"
INDEX_PATH = REPO_ROOT / "website" / "static" / "api" / "skills-index.json"

UI_SKILLS = (
    "ai-native-ui",
)


def _skill_md(name: str) -> Path:
    return UI_DIR / name / "SKILL.md"


def test_ui_skill_dirs_exist_with_skill_md():
    assert (UI_DIR / "DESCRIPTION.md").is_file()
    for name in UI_SKILLS:
        assert _skill_md(name).is_file(), f"missing {_skill_md(name)}"


def test_ui_frontmatter_parses_with_required_fields():
    for name in UI_SKILLS:
        meta = yaml.safe_load(
            _skill_md(name).read_text(encoding="utf-8").split("---")[1]
        )
        assert isinstance(meta, dict), name
        assert str(meta.get("name", "")).strip() == name
        assert str(meta.get("description", "")).strip(), name
        tags = meta["metadata"]["xavani"]["tags"]
        assert isinstance(tags, list) and tags, name


def test_manifest_lists_all_ui_entries():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    listed = {entry["name"] for entry in manifest["skills"]}
    for name in UI_SKILLS:
        assert name in listed, f"{name} missing from MANIFEST.json"


def test_skills_index_contains_built_in_ui_entries():
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    local = {
        entry["name"]
        for entry in index["skills"]
        if entry.get("source") == "oag-skills"
    }
    for name in UI_SKILLS:
        assert name in local, f"{name} missing from skills-index.json"


def test_ai_native_ui_covers_key_primitives_and_tokens():
    text = _skill_md("ai-native-ui").read_text(encoding="utf-8")
    for required in (
        "Approval Card",
        "Task Rows",
        "Tool Chips",
        "dark-mode-first",
        "Context Cards",
        "Streaming Text",
    ):
        assert required in text, f"ai-native-ui missing '{required}'"
