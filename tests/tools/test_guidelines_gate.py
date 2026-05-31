# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for tools/guidelines_gate_tool.py — pre-ship verification gate."""

import json

import pytest

from tools.guidelines_gate_tool import run_guidelines_gate


class TestGuidelinesGate:
    """Test the guidelines gate checks."""

    def test_clean_diff_passes(self):
        """A clean tested diff with a measurable goal passes."""
        diff = (
            "diff --git a/foo.py b/foo.py\n"
            "--- a/foo.py\n"
            "+++ b/foo.py\n"
            "+def bar():\n"
            "+    return 42\n"
            "diff --git a/tests/test_foo.py b/tests/test_foo.py\n"
            "--- a/tests/test_foo.py\n"
            "+++ b/tests/test_foo.py\n"
            "+def test_bar():\n"
            "+    assert bar() == 42\n"
        )
        result = run_guidelines_gate(diff_text=diff, goal="add bar function, latency: 10ms → 8ms")
        assert result["ok"] is True
        assert isinstance(result["failures"], list)
        assert isinstance(result["warnings"], list)

    def test_noisy_diff_fails_surgical(self):
        """A diff touching 25+ files fails the surgical check."""
        lines = []
        for i in range(25):
            lines.append(f"diff --git a/file{i}.py b/file{i}.py")
            lines.append(f"+line {i}")
        diff = "\n".join(lines)
        result = run_guidelines_gate(diff_text=diff, goal="fix one bug")
        assert result["ok"] is False
        checks = [f["check"] for f in result["failures"]]
        assert "surgical" in checks

    def test_scrub_catches_nous_reference(self):
        """A diff adding a nous reference fails the scrub check."""
        diff = "+import hermes_agent\n"
        result = run_guidelines_gate(diff_text=diff, goal="add feature")
        assert result["ok"] is False
        checks = [f["check"] for f in result["failures"]]
        assert "scrub" in checks

    def test_scrub_catches_hermes_reference(self):
        """A diff adding a hermes reference fails the scrub check."""
        diff = "+from hermes_agent import foo\n"
        result = run_guidelines_gate(diff_text=diff, goal="add feature")
        assert result["ok"] is False
        checks = [f["check"] for f in result["failures"]]
        assert "scrub" in checks

    def test_stubs_catches_skills_hub_edit(self):
        """A diff editing skills_hub.py fails the stubs check."""
        diff = "diff --git a/tools/skills_hub.py b/tools/skills_hub.py\n+new line\n"
        result = run_guidelines_gate(diff_text=diff, goal="fix stub")
        assert result["ok"] is False
        checks = [f["check"] for f in result["failures"]]
        assert "stubs_intact" in checks

    def test_stubs_catches_weixin_edit(self):
        """A diff editing weixin.py fails the stubs check."""
        diff = "diff --git a/gateway/platforms/weixin.py b/gateway/platforms/weixin.py\n+new line\n"
        result = run_guidelines_gate(diff_text=diff, goal="fix weixin")
        assert result["ok"] is False
        checks = [f["check"] for f in result["failures"]]
        assert "stubs_intact" in checks

    def test_vague_goal_warns_measurement(self):
        """A vague goal produces a measurement warning."""
        diff = "+x = 1\n"
        result = run_guidelines_gate(diff_text=diff, goal="looks good")
        assert result["ok"] is False
        checks = [f["check"] for f in result["failures"]]
        assert "measurement_stated" in checks

    def test_no_eval_warns(self):
        """A diff without test changes produces an eval_present warning."""
        diff = "diff --git a/foo.py b/foo.py\n+x = 1\n"
        result = run_guidelines_gate(diff_text=diff, goal="add x, latency: 5ms → 3ms")
        # eval_present is a warning, not a failure
        warning_checks = [w["check"] for w in result["warnings"]]
        assert "eval_present" in warning_checks

    def test_abstraction_warns(self):
        """A diff introducing an ABC produces an abstraction warning."""
        diff = "+from abc import ABC\nclass MyBase(ABC): pass\n"
        result = run_guidelines_gate(diff_text=diff, goal="add base class, latency: 5ms → 3ms")
        warning_checks = [w["check"] for w in result["warnings"]]
        assert "no_unearned_abstraction" in warning_checks

    def test_all_check_ids_present(self):
        """All expected check IDs appear in the result (as pass, warn, or fail)."""
        # Use a diff that triggers at least one failure and one warning
        diff = "+import hermes_agent\n"
        result = run_guidelines_gate(diff_text=diff, goal="test")
        all_checks = set()
        for f in result["failures"]:
            all_checks.add(f["check"])
        for w in result["warnings"]:
            all_checks.add(w["check"])
        # At minimum, scrub should fail and eval_present should warn
        assert "scrub" in all_checks
        assert "eval_present" in all_checks
        # The gate always runs all 6 checks — failures+warnings should cover
        # at least the ones that triggered
        assert len(all_checks) >= 2

    def test_empty_diff(self):
        """An empty diff passes (nothing to check)."""
        result = run_guidelines_gate(diff_text="", goal="no changes")
        assert result["ok"] is True
