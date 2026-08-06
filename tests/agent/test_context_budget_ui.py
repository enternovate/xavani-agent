# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for agent/context_budget_ui.py — budget governor UI (harness item 4)."""

from __future__ import annotations

import pytest

from agent.context_budget_ui import (
    BudgetStatus,
    compute_budget_status,
    should_block_new_tools,
    status_to_dict,
)


class TestComputeBudgetStatus:
    def test_ok_below_85(self) -> None:
        status = compute_budget_status(8_000, 10_000)
        assert status.level == "ok"
        assert status.suggestion == ""
        assert status.ratio == pytest.approx(0.8)

    def test_warn_at_85(self) -> None:
        status = compute_budget_status(8_500, 10_000)
        assert status.level == "warn"
        assert "/compact recommended" in status.suggestion

    def test_warn_above_85_below_95(self) -> None:
        status = compute_budget_status(9_000, 10_000)
        assert status.level == "warn"
        assert "90%" in status.suggestion

    def test_block_at_95(self) -> None:
        status = compute_budget_status(9_500, 10_000)
        assert status.level == "block"
        assert "/compact required" in status.suggestion

    def test_block_above_95(self) -> None:
        status = compute_budget_status(9_999, 10_000)
        assert status.level == "block"

    def test_disabled_limit_returns_ok(self) -> None:
        status = compute_budget_status(50_000, 0)
        assert status.level == "ok"
        assert status.suggestion == ""

    def test_negative_usage_clamps_to_ok(self) -> None:
        status = compute_budget_status(-5, 10_000)
        assert status.level == "ok"


class TestShouldBlockNewTools:
    def test_block_level_blocks(self) -> None:
        assert should_block_new_tools(BudgetStatus(9_500, 10_000, 0.95, "block", "x")) is True

    def test_warn_level_does_not_block(self) -> None:
        assert should_block_new_tools(BudgetStatus(8_500, 10_000, 0.85, "warn", "x")) is False

    def test_ok_level_does_not_block(self) -> None:
        assert should_block_new_tools(BudgetStatus(1_000, 10_000, 0.1, "ok", "")) is False


class TestStatusToDict:
    def test_serialises_fields(self) -> None:
        status = compute_budget_status(8_500, 10_000)
        d = status_to_dict(status)
        assert d["used_tokens"] == 8_500
        assert d["limit_tokens"] == 10_000
        assert d["level"] == "warn"
        assert d["ratio"] == pytest.approx(0.85)
        assert "suggestion" in d
