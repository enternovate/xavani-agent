# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""C03: Real-time dashboard TUI tests.

Tests the data-source functions (collect_snapshot, render_snapshot).
The curses loop itself is not testable without a tty and is not tested.
"""

from xavani_observability.cost_attribution import CostLedger
from xavani_observability.dashboard_tui import collect_snapshot, render_snapshot
from xavani_observability.error_budget import ErrorBudget
from xavani_observability.metrics import MetricsCollector

import pytest


def _collector(tmp_path):
    return MetricsCollector(persist_path=tmp_path / "metrics.json")


def test_snapshot_active_agents_and_queue(tmp_path):
    collector = _collector(tmp_path)
    collector.record_session_start()
    collector.record_session_start()
    snapshot = collect_snapshot(collector, budgets={}, queue_size=3)
    assert snapshot["active_agents"] == 2
    assert snapshot["queue_depth"] == 3


def test_snapshot_models(tmp_path):
    collector = _collector(tmp_path)
    collector.record_llm_latency("claude-sonnet", 100.0)
    collector.record_llm_latency("claude-sonnet", 300.0)
    snapshot = collect_snapshot(collector, budgets={})
    assert len(snapshot["models"]) == 1
    row = snapshot["models"][0]
    assert row["model"] == "claude-sonnet"
    assert row["calls"] == 2
    assert row["avg_ms"] == 200.0
    # Percentile contract: metrics._percentile interpolates; p95 of [100, 300] is 290.0.
    assert row["p95_ms"] == 290.0


def test_snapshot_tools_with_errors(tmp_path):
    collector = _collector(tmp_path)
    collector.record_tool_latency("read_file", 50.0)
    collector.record_tool_latency("read_file", 150.0)
    collector.record_tool_error("read_file", "timeout")
    snapshot = collect_snapshot(collector, budgets={})
    assert len(snapshot["tools"]) == 1
    row = snapshot["tools"][0]
    assert row["tool"] == "read_file"
    assert row["calls"] == 2
    assert row["avg_ms"] == 100.0
    assert row["error_rate_pct"] == 50.0
    assert snapshot["total_errors"] == 1


def test_snapshot_budgets_from_explicit_map(tmp_path):
    collector = _collector(tmp_path)
    budget = ErrorBudget("tools", slo=0.99)
    budget.record(True)
    budget.record(False)
    snapshot = collect_snapshot(
        collector, budgets={"tools": budget}
    )
    assert len(snapshot["budgets"]) == 1
    row = snapshot["budgets"][0]
    assert row["subsystem"] == "tools"
    assert row["slo"] == 0.99
    assert row["availability"] == 0.5
    # Budget remaining is availability relative to the SLO (0.5 / 0.99).
    assert row["remaining"] == pytest.approx(0.5 / 0.99)


def test_snapshot_idle_budget_is_none(tmp_path):
    collector = _collector(tmp_path)
    budget = ErrorBudget("tools")
    snapshot = collect_snapshot(collector, budgets={"tools": budget})
    row = snapshot["budgets"][0]
    assert row["availability"] is None
    assert row["remaining"] is None


def test_snapshot_cost_burn(tmp_path):
    collector = _collector(tmp_path)
    ledger = CostLedger()
    ledger.record("s1", "t1", "claude-sonnet", 0.25)
    ledger.record("s1", "t2", "claude-sonnet", 0.05)
    snapshot = collect_snapshot(collector, budgets={}, ledger=ledger)
    assert snapshot["cost_burn_usd"] == 0.3


def test_snapshot_cost_zero_without_ledger(tmp_path):
    collector = _collector(tmp_path)
    snapshot = collect_snapshot(collector, budgets={})
    assert snapshot["cost_burn_usd"] == 0.0


def test_render_snapshot_sections(tmp_path):
    collector = _collector(tmp_path)
    collector.record_session_start()
    collector.record_llm_latency("claude-sonnet", 100.0)
    collector.record_tool_latency("read_file", 50.0)
    budget = ErrorBudget("tools")
    budget.record(True)
    snapshot = collect_snapshot(
        collector, budgets={"tools": budget}, queue_size=2
    )
    lines = render_snapshot(snapshot)
    text = "\n".join(lines)
    assert "Xavani dashboard" in text
    assert "active agents: 1" in text
    assert "queue: 2" in text
    assert "models:" in text
    assert "claude-sonnet" in text
    assert "tools:" in text
    assert "read_file" in text
    assert "error budgets:" in text
    assert "tools" in text


def test_render_snapshot_empty(tmp_path):
    collector = _collector(tmp_path)
    snapshot = collect_snapshot(
        collector, budgets={"tools": ErrorBudget("tools")}
    )
    lines = render_snapshot(snapshot)
    text = "\n".join(lines)
    assert "active agents: 0" in text
    assert "models: none" in text
    assert "tools: none" in text
    assert "n/a" in text  # idle budgets render as n/a


def test_render_snapshot_deterministic(tmp_path):
    collector = _collector(tmp_path)
    collector.record_llm_latency("claude-sonnet", 100.0)
    snapshot = collect_snapshot(collector, budgets={})
    assert render_snapshot(snapshot) == render_snapshot(snapshot)
