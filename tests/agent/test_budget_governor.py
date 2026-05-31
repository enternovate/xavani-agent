# Copyright (c) 2025-2026 Enternovate.
# MIT License — See LICENSE file for full terms.
# Built by Enternovate — Open source. Private. Local.

"""Tests for agent/budget_governor.py — session token/cost budget governor."""

import pytest

from agent.budget_governor import SessionBudgetGovernor, SessionUsage


class TestSessionUsage:
    def test_defaults(self):
        usage = SessionUsage()
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0
        assert usage.cache_read_tokens == 0
        assert usage.total_cost_usd == 0.0
        assert usage.turn_count == 0


class TestSessionBudgetGovernor:
    def test_record_usage_accumulates(self):
        g = SessionBudgetGovernor(budget_usd=1.0)
        g.record_usage({"input_tokens": 100, "output_tokens": 50, "cost_usd": 0.10})
        g.record_usage({"input_tokens": 200, "output_tokens": 100, "cost_usd": 0.20})
        assert g.usage.input_tokens == 300
        assert g.usage.output_tokens == 150
        assert g.usage.total_cost_usd == pytest.approx(0.30)
        assert g.usage.turn_count == 2

    def test_record_usage_handles_none(self):
        g = SessionBudgetGovernor()
        g.record_usage({"input_tokens": None, "output_tokens": None, "cost_usd": None})
        assert g.usage.input_tokens == 0
        assert g.usage.output_tokens == 0
        assert g.usage.total_cost_usd == 0.0

    def test_is_over_budget_cost(self):
        g = SessionBudgetGovernor(budget_usd=1.0)
        g.record_usage({"cost_usd": 0.50})
        assert g.is_over_budget() is False
        g.record_usage({"cost_usd": 0.60})
        assert g.is_over_budget() is True

    def test_is_over_budget_tokens(self):
        g = SessionBudgetGovernor(budget_input_tokens=1000)
        g.record_usage({"input_tokens": 500})
        assert g.is_over_budget() is False
        g.record_usage({"input_tokens": 600})
        assert g.is_over_budget() is True

    def test_should_warn_at_threshold(self):
        g = SessionBudgetGovernor(budget_usd=1.0, warn_threshold=0.8)
        g.record_usage({"cost_usd": 0.50})
        assert g.should_warn() is False
        g.record_usage({"cost_usd": 0.35})
        assert g.should_warn() is True

    def test_should_warn_only_once(self):
        g = SessionBudgetGovernor(budget_usd=1.0, warn_threshold=0.8)
        g.record_usage({"cost_usd": 0.90})
        assert g.should_warn() is True
        # Second call should return False (already warned)
        assert g.should_warn() is False

    def test_status_format(self):
        g = SessionBudgetGovernor(budget_usd=2.0)
        g.record_usage({"input_tokens": 1000, "output_tokens": 500, "cost_usd": 1.0})
        s = g.status()
        assert s["turns"] == 1
        assert s["input_tokens"] == 1000
        assert s["output_tokens"] == 500
        assert s["total_cost_usd"] == 1.0
        assert s["cost_pct"] == "50.0%"
        assert s["over_budget"] is False

    def test_format_warning(self):
        g = SessionBudgetGovernor(budget_usd=1.0)
        g.record_usage({"cost_usd": 0.90})
        warning = g.format_warning()
        assert "budget warning" in warning
        assert "$0.90" in warning

    def test_no_budget_never_over(self):
        """With no budget set, is_over_budget is always False."""
        g = SessionBudgetGovernor()
        g.record_usage({"cost_usd": 999999, "input_tokens": 999999999})
        assert g.is_over_budget() is False
        assert g.should_warn() is False
