# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for agent/self_critique.py — self-critique pass (harness item 3)."""

from __future__ import annotations

import pytest

from agent.self_critique import (
    DEFAULT_RUBRIC,
    RubricError,
    build_review_prompt,
    extract_fix,
    parse_rubric,
    run_self_critique,
)


class TestParseRubric:
    def test_valid_rubric_passes(self) -> None:
        assert parse_rubric({"correctness": "Is it right?"}) == {"correctness": "Is it right?"}

    def test_default_rubric_parses(self) -> None:
        parsed = parse_rubric(DEFAULT_RUBRIC)
        assert set(parsed) == {"correctness", "completeness", "citations", "ste_compliance"}

    def test_non_dict_raises(self) -> None:
        with pytest.raises(RubricError):
            parse_rubric(["not", "a", "dict"])

    def test_blank_criterion_raises(self) -> None:
        with pytest.raises(RubricError):
            parse_rubric({"correctness": "   "})

    def test_empty_rubric_raises(self) -> None:
        with pytest.raises(RubricError):
            parse_rubric({})


class TestBuildReviewPrompt:
    def test_prompt_contains_answer_and_criteria(self) -> None:
        prompt = build_review_prompt("The answer.", DEFAULT_RUBRIC)
        assert "The answer." in prompt
        assert "correctness" in prompt
        assert "FIX:" in prompt


class TestExtractFix:
    def test_extracts_after_marker(self) -> None:
        review = "Needs work.\nFIX:\nThe fixed answer."
        assert extract_fix(review) == "The fixed answer."

    def test_no_marker_returns_none(self) -> None:
        assert extract_fix("Looks good. OK") is None

    def test_empty_fix_returns_none(self) -> None:
        assert extract_fix("FIX:\n   \n") is None


class TestRunSelfCritique:
    def test_disabled_returns_original(self) -> None:
        result = run_self_critique("orig", lambda p: "FIX:\nchanged", enabled=False)
        assert result == {"answer": "orig", "fixed": False, "iterations": 0}

    def test_ok_review_keeps_answer(self) -> None:
        result = run_self_critique("orig", lambda p: "OK")
        assert result["answer"] == "orig"
        assert result["fixed"] is False
        assert result["iterations"] == 0

    def test_fix_applied_once(self) -> None:
        result = run_self_critique("orig", lambda p: "FIX:\nbetter")
        assert result["answer"] == "better"
        assert result["fixed"] is True
        assert result["iterations"] == 1

    def test_loop_is_bounded_to_one_iteration(self) -> None:
        calls: list[str] = []

        def always_fix(prompt: str) -> str:
            calls.append(prompt)
            return "FIX:\nstill fixing"

        result = run_self_critique("orig", always_fix)
        assert result["iterations"] == 1
        assert len(calls) == 1  # never a second fix pass

    def test_bad_rubric_raises_even_when_enabled(self) -> None:
        with pytest.raises(RubricError):
            run_self_critique("orig", lambda p: "OK", rubric={"x": ""})
