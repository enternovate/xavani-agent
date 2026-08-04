# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""C05: cost attribution tests."""

import pytest

import xavani_observability.cost_attribution as ca
from xavani_observability.cost_attribution import (
    CostLedger,
    cost_ledger,
    record_attributed_cost,
    reset_cost_ledger,
)


@pytest.fixture(autouse=True)
def _clean():
    reset_cost_ledger()
    yield
    reset_cost_ledger()


# ── ledger math ─────────────────────────────────────────────────────


def test_record_and_session_cost():
    ledger = CostLedger()
    ledger.record("s1", "t1", "model-a", 0.10)
    ledger.record("s1", "t2", "model-b", 0.05)
    assert ledger.session_cost("s1") == pytest.approx(0.15)
    assert ledger.session_cost("s2") == 0.0


def test_zero_cost_ignored():
    ledger = CostLedger()
    ledger.record("s1", "t1", "m", 0.0)
    ledger.record("s1", "t1", "m", -1.0)
    assert ledger.session_cost("s1") == 0.0


def test_report_aggregates_by_session():
    ledger = CostLedger()
    ledger.record("s1", "t1", "m", 0.10)
    ledger.record("s1", "t2", "m", 0.20)
    ledger.record("s2", "t1", "m", 0.05)
    report = ledger.report()
    assert report["total_usd"] == pytest.approx(0.35)
    assert report["by_session"]["s1"] == pytest.approx(0.30)
    assert report["by_session"]["s2"] == pytest.approx(0.05)


def test_report_aggregates_by_task():
    ledger = CostLedger()
    ledger.record("s1", "t1", "m", 0.10)
    ledger.record("s1", "t1", "m", 0.05)
    ledger.record("s1", "t2", "m", 0.02)
    report = ledger.report()
    assert report["by_task"]["s1::t1"] == pytest.approx(0.15)
    assert report["by_task"]["s1::t2"] == pytest.approx(0.02)


def test_report_aggregates_by_model():
    ledger = CostLedger()
    ledger.record("s1", "t1", "cheap", 0.01)
    ledger.record("s1", "t2", "pricey", 0.99)
    report = ledger.report()
    assert report["by_model"]["pricey"] == pytest.approx(0.99)
    assert report["by_model"]["cheap"] == pytest.approx(0.01)


def test_report_window_filters_old():
    import time as _time

    ledger = CostLedger()
    now = _time.time()
    ledger.record("s1", "t1", "m", 0.50, now=now - 48 * 3600)  # 2 days old
    ledger.record("s1", "t1", "m", 0.10, now=now)
    report = ledger.report(hours=24)
    assert report["total_usd"] == pytest.approx(0.10)


def test_report_sorts_descending():
    ledger = CostLedger()
    ledger.record("s1", "t1", "m", 0.01)
    ledger.record("s2", "t1", "m", 0.99)
    report = ledger.report()
    assert list(report["by_session"].keys()) == ["s2", "s1"]


def test_reset_clears():
    ledger = CostLedger()
    ledger.record("s1", "t1", "m", 0.10)
    ledger.reset()
    assert ledger.session_cost("s1") == 0.0


# ── singleton ───────────────────────────────────────────────────────


def test_ledger_singleton():
    ledger1 = cost_ledger()
    ledger2 = cost_ledger()
    assert ledger1 is ledger2


def test_record_attributed_feeds_singleton():
    reset_cost_ledger()
    record_attributed_cost("s9", "t9", "model-x", 0.25)
    assert cost_ledger().session_cost("s9") == pytest.approx(0.25)


def test_record_attributed_never_raises():
    record_attributed_cost("", "", "", 0.01)  # odd inputs still fine
    record_attributed_cost("s", "t", "m", 0.0)
