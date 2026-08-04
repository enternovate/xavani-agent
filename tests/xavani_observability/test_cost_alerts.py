# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""D04: cost-per-minute spending guard tests."""

import pytest

import xavani_observability.cost_alerts as ca
from xavani_observability.cost_alerts import (
    CostGuard,
    configured_threshold,
    cost_guard,
    record_call_cost,
    reset_cost_guard,
)


@pytest.fixture(autouse=True)
def _clean_guard():
    reset_cost_guard()
    yield
    reset_cost_guard()


# ── burn rate math ──────────────────────────────────────────────────


def test_idle_rate_zero():
    g = CostGuard()
    assert g.burn_rate_per_minute() == 0.0
    assert g.exceeded() is False


def test_rate_scales_with_costs():
    g = CostGuard(threshold=2.0)
    now = 1_000_000.0
    # $0.50 over 1 minute window (6 buckets of 30s... use 2 records).
    g.record(0.50, now=now)
    g.record(0.50, now=now + 30)
    # Window spans ~60s -> ~$1.0/min (rate = total/elapsed).
    rate = g.burn_rate_per_minute(now=now + 60)
    assert rate == pytest.approx(1.0, abs=0.05)


def test_exceeded_threshold():
    g = CostGuard(threshold=1.0)
    now = 2_000_000.0
    g.record(2.0, now=now)
    assert g.exceeded(now=now + 30) is True


def test_below_threshold_not_exceeded():
    g = CostGuard(threshold=10.0)
    now = 3_000_000.0
    g.record(1.0, now=now)
    assert g.exceeded(now=now + 60) is False


def test_window_prunes_old_costs():
    g = CostGuard(threshold=1.0)
    now = 4_000_000.0
    g.record(50.0, now=now - 3_600)  # 1h ago — outside window
    g.record(0.0, now=now)
    assert g.burn_rate_per_minute(now=now) == 0.0


def test_zero_cost_ignored():
    g = CostGuard()
    g.record(0.0)
    g.record(-1.0)
    assert g.burn_rate_per_minute() == 0.0


def test_snapshot_shape():
    g = CostGuard(threshold=2.0)
    g.record(0.25)
    snap = g.snapshot()
    assert "burn_rate_usd_per_min" in snap
    assert snap["threshold_usd_per_min"] == 2.0
    assert snap["window_total_usd"] == 0.25
    assert "exceeded" in snap


# ── config + singleton ──────────────────────────────────────────────


def test_default_threshold():
    assert configured_threshold() == 2.0


def test_threshold_env(monkeypatch):
    monkeypatch.setenv("XAVANI_COST_PER_MINUTE_ALERT", "5.5")
    assert configured_threshold() == 5.5
    monkeypatch.setenv("XAVANI_COST_PER_MINUTE_ALERT", "junk")
    assert configured_threshold() == 2.0


def test_cost_guard_singleton():
    g1 = cost_guard()
    g2 = cost_guard()
    assert g1 is g2


def test_record_call_cost_feeds_guard():
    reset_cost_guard()
    record_call_cost(0.10)
    assert cost_guard().snapshot()["window_total_usd"] == 0.10


# ── metrics collector integration ───────────────────────────────────


def test_collector_record_cost_feeds_guard():
    from xavani_observability.metrics import MetricsCollector

    reset_cost_guard()
    mc = MetricsCollector(persist_path=None)
    mc.record_cost(0.05)
    assert cost_guard().snapshot()["window_total_usd"] == 0.05
