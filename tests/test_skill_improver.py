# Copyright (c) 2025-2026 Enternovate.
# MIT License — See LICENSE file for full terms.
# Built by Enternovate — Open source. Private. Local.

"""Tests for xavani_learner/skill_improver.py — skill auto-improvement loop."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from xavani_learner.skill_improver import (
    extract_pattern_from_trajectory,
    propose_skill_draft,
    list_drafts,
    approve_draft,
    discard_draft,
    _generate_skill_name,
    _draft_dir,
)


@pytest.fixture(autouse=True)
def _use_tmp_drafts(tmp_path):
    """Redirect draft storage to tmp_path."""
    with patch("xavani_learner.skill_improver._draft_dir", return_value=tmp_path):
        yield tmp_path


class TestGenerateSkillName:
    def test_basic_slug(self):
        name = _generate_skill_name("Build a trading bot")
        assert name == "build-a-trading-bot"

    def test_special_chars_removed(self):
        name = _generate_skill_name("Fix the bug!!! @#$%")
        assert name == "fix-the-bug"

    def test_long_description_truncated(self):
        name = _generate_skill_name("a b c d e f g h i j k l m n o p")
        assert name == "a-b-c-d-e"

    def test_empty_description(self):
        name = _generate_skill_name("")
        assert name == "unnamed-skill"


class TestExtractPattern:
    def test_basic_extraction(self):
        pattern = extract_pattern_from_trajectory(
            task_description="Build a parser",
            steps_taken=["Read input", "Parse tokens", "Build AST"],
            tools_used=["read_file", "write_file"],
            outcome="Parser working with 100% pass rate",
            eval_pass_rate=100.0,
        )
        assert pattern["name"] == "build-a-parser"
        assert len(pattern["steps"]) == 3
        assert pattern["eval_pass_rate"] == 100.0

    def test_category_from_tools(self):
        pattern = extract_pattern_from_trajectory(
            task_description="deploy service",
            steps_taken=["step 1"],
            tools_used=["terminal"],
            outcome="deployed",
        )
        assert pattern["category"] == "devops"


class TestProposeDraft:
    def test_creates_draft_file(self, tmp_path):
        pattern = extract_pattern_from_trajectory(
            task_description="test skill",
            steps_taken=["step 1", "step 2"],
            tools_used=["read_file"],
            outcome="done",
            eval_pass_rate=95.0,
        )
        result = propose_skill_draft(pattern)
        assert result["ok"] is True
        draft_path = Path(result["path"])
        assert draft_path.exists()
        content = draft_path.read_text()
        assert "DRAFT" in content
        assert "test-skill" in content

    def test_duplicate_rejected(self, tmp_path):
        pattern = extract_pattern_from_trajectory(
            task_description="dup test",
            steps_taken=["step 1"],
            tools_used=["read_file"],
            outcome="done",
        )
        propose_skill_draft(pattern)
        result = propose_skill_draft(pattern)
        assert result["ok"] is False
        assert "already exists" in result["message"]

    def test_force_overwrites(self, tmp_path):
        pattern = extract_pattern_from_trajectory(
            task_description="force test",
            steps_taken=["step 1"],
            tools_used=["read_file"],
            outcome="done",
        )
        propose_skill_draft(pattern)
        result = propose_skill_draft(pattern, force=True)
        assert result["ok"] is True

    def test_draft_never_writes_to_skills(self, tmp_path):
        """Drafts go to tmp_path (mocked draft dir), not to skills/."""
        pattern = extract_pattern_from_trajectory(
            task_description="safety test",
            steps_taken=["step 1"],
            tools_used=["read_file"],
            outcome="done",
        )
        result = propose_skill_draft(pattern)
        assert "skills/" not in result["path"]


class TestDraftManagement:
    def test_list_drafts(self, tmp_path):
        pattern = extract_pattern_from_trajectory(
            task_description="list test",
            steps_taken=["step 1"],
            tools_used=["read_file"],
            outcome="done",
        )
        propose_skill_draft(pattern)
        drafts = list_drafts()
        assert len(drafts) == 1
        assert drafts[0]["name"] == "list-test"

    def test_approve_draft(self, tmp_path):
        pattern = extract_pattern_from_trajectory(
            task_description="approve test",
            steps_taken=["step 1"],
            tools_used=["read_file"],
            outcome="done",
        )
        propose_skill_draft(pattern)
        result = approve_draft("approve-test", target_dir=str(tmp_path / "promoted"))
        assert result["ok"] is True
        assert "promoted" in result["path"]
        # Draft should be removed
        drafts = list_drafts()
        assert len(drafts) == 0

    def test_discard_draft(self, tmp_path):
        pattern = extract_pattern_from_trajectory(
            task_description="discard test",
            steps_taken=["step 1"],
            tools_used=["read_file"],
            outcome="done",
        )
        propose_skill_draft(pattern)
        result = discard_draft("discard-test")
        assert result["ok"] is True
        drafts = list_drafts()
        assert len(drafts) == 0
