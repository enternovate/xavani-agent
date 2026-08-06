# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""B04: learn prompt pack tests."""

from __future__ import annotations

from agent.learn_prompt import (
    LearnDraft,
    extract_learn_draft,
    learn_from_correction,
    render_skill_draft,
    save_skill_draft,
)


def test_extract_splits_first_sentence_as_rule():
    draft = extract_learn_draft(
        "Always run tests before committing. I forgot last time and CI broke."
    )
    assert draft.rule == "Always run tests before committing."
    assert "CI broke" in draft.example
    assert draft.title


def test_explicit_markers_win():
    draft = extract_learn_draft(
        "rule: Never use bare except.\nexample: except Exception as e: pass\n"
    )
    assert draft.rule == "Never use bare except."
    assert draft.example == "except Exception as e: pass"


def test_empty_correction_returns_empty_draft():
    draft = extract_learn_draft("   ")
    assert draft.rule == ""


def test_render_produces_skill_markdown():
    draft = LearnDraft(title="Test First", rule="Run tests before commits.", example="pytest -q")
    md = render_skill_draft(draft)
    assert "name: test-first" in md
    assert "## Rule" in md
    assert "Run tests before commits." in md
    assert "## Example" in md


def test_save_stages_into_pending_skills(tmp_path):
    draft = LearnDraft(title="Test First", rule="Run tests first.", source="user")
    path = save_skill_draft(draft, home=tmp_path)
    assert path == tmp_path / "pending" / "skills" / "test-first.md"
    assert path.exists()
    assert "Source: user" in path.read_text(encoding="utf-8")


def test_learn_pipeline_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("XAVANI_HOME", str(tmp_path))
    result = learn_from_correction(
        "Always check the exit code. The script failed silently.",
        source="session-1",
    )
    assert result["ok"] is True
    assert result["path"].endswith(".md")
    assert "Always check the exit code." in result["markdown"]


def test_learn_pipeline_rejects_empty():
    result = learn_from_correction("")
    assert result["ok"] is False
