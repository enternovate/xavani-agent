# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for tools/guidelines_gate_tool.py — pre-ship verification gate."""

import json

import pytest

from tools.guidelines_gate_tool import run_guidelines_gate

pytestmark = pytest.mark.unit


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

    def test_skills_hub_edit_is_no_longer_a_path_ban(self):
        """The implemented skills hub is no longer treated as a stub (Task 24a).

        Contract change: this replaces the old
        ``test_stubs_catches_skills_hub_edit`` assertion, which encoded the
        stale ``_STUB_FILES`` path ban. skills_hub.py is a shipped module, so
        editing it must not fail the gate.
        """
        diff = "diff --git a/tools/skills_hub.py b/tools/skills_hub.py\n+new line\n"
        result = run_guidelines_gate(diff_text=diff, goal="extend the skills hub, latency: 5ms → 3ms")
        checks = [f["check"] for f in result["failures"]]
        assert "prohibited_services" not in checks
        assert "stubs_intact" not in checks
        assert result["ok"] is True

    def test_weixin_platform_edit_is_no_longer_a_path_ban(self):
        """The weixin platform adapter is shipped code, not a stub (Task 24a).

        Contract change: this replaces the old
        ``test_stubs_catches_weixin_edit`` assertion.
        """
        diff = "diff --git a/gateway/platforms/weixin.py b/gateway/platforms/weixin.py\n+new line\n"
        result = run_guidelines_gate(diff_text=diff, goal="extend the weixin adapter, latency: 5ms → 3ms")
        checks = [f["check"] for f in result["failures"]]
        assert "stubs_intact" not in checks
        assert result["ok"] is True

    def test_prohibited_services_flags_an_upstream_portal_host(self):
        """A diff adding an upstream subscription/portal host fails (Code Pack Q)."""
        diff = '+PORTAL = "https://portal.nousresearch.com/checkout"\n'
        result = run_guidelines_gate(diff_text=diff, goal="add a product button, latency: 5ms → 3ms")
        assert result["ok"] is False
        checks = [f["check"] for f in result["failures"]]
        assert "prohibited_services" in checks

    def test_prohibited_services_ignores_a_mere_mention_of_disabled(self):
        """`# not disabled` must not exempt an enabled default (review probe)."""
        diff = "+telemetry = true  # not disabled\n"
        result = run_guidelines_gate(diff_text=diff, goal="add feature")
        checks = [f["check"] for f in result["failures"]]
        assert "prohibited_services" in checks

    def test_prohibited_services_allows_an_explicit_disable(self):
        diff = "+telemetry = false\n"
        result = run_guidelines_gate(diff_text=diff, goal="add feature")
        checks = [f["check"] for f in result["failures"]]
        assert "prohibited_services" not in checks

    def test_prohibited_services_flags_default_telemetry(self):
        """A diff enabling telemetry by default fails."""
        diff = "+telemetry_enabled = True\n"
        result = run_guidelines_gate(diff_text=diff, goal="add feature, latency: 5ms → 3ms")
        assert result["ok"] is False
        checks = [f["check"] for f in result["failures"]]
        assert "prohibited_services" in checks

    def test_prohibited_services_flags_an_unopted_upstream_update_target(self):
        """A diff pointing an update check at an upstream host fails."""
        diff = '+update_url = "https://portal.nousresearch.com/latest"\n'
        result = run_guidelines_gate(diff_text=diff, goal="add update check, latency: 5ms → 3ms")
        checks = [f["check"] for f in result["failures"]]
        assert "prohibited_services" in checks

    def test_prohibited_services_warns_on_an_undeclared_network_call(self):
        """A new network call to an undeclared host is flagged for review."""
        diff = '+requests.get("https://tracker.example.net/collect")\n'
        result = run_guidelines_gate(diff_text=diff, goal="add a client, latency: 5ms → 3ms")
        warning_checks = [w["check"] for w in result["warnings"]]
        assert "prohibited_services" in warning_checks

    def test_prohibited_services_allows_an_explicit_provider_selection(self):
        """A user-selected provider endpoint is not a product surface (Code Pack Q)."""
        diff = '+base_url = "https://api.openai.com/v1"\n'
        result = run_guidelines_gate(diff_text=diff, goal="add provider, latency: 5ms → 3ms")
        checks = [f["check"] for f in result["failures"] + result["warnings"]]
        assert "prohibited_services" not in checks

    def test_prohibited_services_exempts_legal_attribution(self):
        """Legal files may retain upstream attribution (Task 24a)."""
        diff = (
            "diff --git a/THIRD_PARTY_NOTICES.md b/THIRD_PARTY_NOTICES.md\n"
            "+Copyright (c) 2025 Nous Research — https://github.com/NousResearch/hermes-agent\n"
        )
        result = run_guidelines_gate(diff_text=diff, goal="add notices, latency: 5ms → 3ms")
        checks = [f["check"] for f in result["failures"] + result["warnings"]]
        assert "prohibited_services" not in checks

    def test_prohibited_services_allows_owned_hosts(self):
        """An owned release page stays allowed."""
        diff = '+URL = "https://github.com/enternovate/xavani-agent/releases/tag/v0.4.0"\n'
        result = run_guidelines_gate(diff_text=diff, goal="add release link, latency: 5ms → 3ms")
        checks = [f["check"] for f in result["failures"] + result["warnings"]]
        assert "prohibited_services" not in checks

    def test_prohibited_apex_domains_match_the_boundary_scanner(self):
        """The gate and the Task 24a scanner share one prohibited-host list."""
        from scripts import check_product_boundary as boundary
        from tools.guidelines_gate_tool import PROHIBITED_APEX_DOMAINS

        assert PROHIBITED_APEX_DOMAINS == boundary.UPSTREAM_APEX_DOMAINS

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
        # at least the ones that triggered (scrub, eval_present, prohibited_services)
        assert len(all_checks) >= 2

    def test_empty_diff(self):
        """An empty diff passes (nothing to check)."""
        result = run_guidelines_gate(diff_text="", goal="no changes")
        assert result["ok"] is True
