# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""C02 — model cost guard tests."""

from __future__ import annotations

import pytest

from xavani_cli.model_cost_guard import model_cost_guard


class TestModelCostGuard:
    def test_cheap_model_no_warning(self):
        assert model_cost_guard("gpt-4o-mini", 0.15, provider="openai") is None

    def test_expensive_model_warns(self):
        msg = model_cost_guard("claude-opus-4-1", 25.0, provider="anthropic")
        assert msg is not None
        assert "Cost guard" in msg
        assert "$25.00/M" in msg
        assert "anthropic/claude-opus-4-1" in msg

    def test_exactly_at_threshold_no_warning(self):
        assert model_cost_guard("m", 20.0) is None

    def test_unknown_cost_no_warning(self):
        assert model_cost_guard("m", 0.0) is None
        assert model_cost_guard("m", None) is None

    def test_negative_cost_ignored(self):
        assert model_cost_guard("m", -1.0) is None

    def test_custom_threshold(self):
        assert model_cost_guard("m", 5.0, threshold=10.0) is None
        assert model_cost_guard("m", 15.0, threshold=10.0) is not None

    def test_no_provider_label_when_empty(self):
        msg = model_cost_guard("pricey", 99.0)
        assert msg is not None
        assert "/pricey" not in msg
        assert "pricey is $99.00/M" in msg
