# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""E06: error budget tracking per subsystem."""

import time

from xavani_observability.error_budget import (
    SUBSYSTEM_SLOS,
    ErrorBudget,
    get_tool_budget,
    record_tool_outcome,
)


def test_default_slos():
    assert SUBSYSTEM_SLOS["gateway"] == 0.999
    assert SUBSYSTEM_SLOS["agent"] == 0.995
    assert SUBSYSTEM_SLOS["tools"] == 0.99


def test_idle_budget_no_data():
    b = ErrorBudget("gateway")
    assert b.availability() is None
    assert b.budget_remaining() is None
    assert b.violated() is False
    s = b.summary()
    assert s["availability"] is None
    assert s["violated"] is False


def test_all_success_full_budget():
    b = ErrorBudget("gateway", slo=0.999)
    for _ in range(100):
        b.record(True)
    assert b.availability() == 1.0
    assert b.budget_remaining() == 1.0
    assert b.violated() is False


def test_failures_violate_budget():
    b = ErrorBudget("gateway", slo=0.9)
    for _ in range(90):
        b.record(True)
    for _ in range(10):
        b.record(False)
    # 90% availability == exactly the SLO, not below.
    assert b.violated() is False
    b.record(False)  # 90/101 -> below 90%
    assert b.violated() is True


def test_budget_remaining_partial():
    b = ErrorBudget("tools", slo=0.99)
    for _ in range(99):
        b.record(True)
    b.record(False)  # 99% availability
    assert b.budget_remaining() == 1.0
    for _ in range(100):
        b.record(False)
    # 99/200 = 49.5% availability -> 49.5/99 = 50% budget remaining.
    assert b.budget_remaining() == 0.5


def test_window_prunes_old_buckets():
    b = ErrorBudget("tools", slo=0.99)
    now = time.time()
    # 100 successes at t=0...
    for _ in range(100):
        b.record(True, now=now - 7200)  # 2h ago — outside the 1h window
    # ...and 1 failure now.
    b.record(False, now=now)
    summary = b.summary()
    # Old successes pruned; only the failure remains in the window.
    assert summary["success_count"] == 0
    assert summary["failure_count"] == 1
    assert summary["availability"] == 0.0


def test_summary_shape():
    b = ErrorBudget("cron")
    b.record(True)
    s = b.summary()
    assert s["subsystem"] == "cron"
    assert s["total_count"] == 1
    assert s["success_count"] == 1
    assert "budget_remaining" in s
    assert "violated" in s


# ── process-wide singleton + metrics collector wiring ───────────────


def test_record_tool_outcome_feeds_singleton():
    record_tool_outcome(True)
    record_tool_outcome(False)
    budget = get_tool_budget()
    assert budget.subsystem == "tools"
    s = budget.summary()
    assert s["total_count"] >= 2


def test_metrics_collector_feeds_tool_budget():
    from xavani_observability.metrics import MetricsCollector

    mc = MetricsCollector(persist_path=None)
    before = get_tool_budget().summary()["total_count"]
    mc.record_tool_latency("read_file", 1.0)
    mc.record_tool_error("read_file", "timeout")
    after = get_tool_budget().summary()["total_count"]
    assert after == before + 2
