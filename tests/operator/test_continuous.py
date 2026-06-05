# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for continuous operation: quiet hours, locks, backpressure, run loop
(v0.7.0 operator U81/U83/U85/U87)."""

from __future__ import annotations

from datetime import datetime

from xavani_operator.approval_queue import ApprovalQueue
from xavani_operator.config import ProductConfig, ProductInfo
from xavani_operator.continuous import (
    acquire_lock,
    backpressure_ok,
    in_quiet_hours,
    release_lock,
    run_continuous,
)
from xavani_operator.propose import make_proposal
from xavani_operator.state import OperatorState
from xavani_operator.types import Intent, Opportunity


def _cfg(**kw):
    return ProductConfig(product=ProductInfo(name="X"), **kw)


# --- U83: quiet hours -------------------------------------------------------

def test_quiet_hours_overnight():
    assert in_quiet_hours("22:00-06:00", datetime(2026, 1, 1, 23, 0)) is True
    assert in_quiet_hours("22:00-06:00", datetime(2026, 1, 1, 3, 0)) is True
    assert in_quiet_hours("22:00-06:00", datetime(2026, 1, 1, 12, 0)) is False


def test_quiet_hours_same_day():
    assert in_quiet_hours("09:00-17:00", datetime(2026, 1, 1, 12, 0)) is True
    assert in_quiet_hours("09:00-17:00", datetime(2026, 1, 1, 20, 0)) is False


def test_quiet_hours_empty_is_never_quiet():
    assert in_quiet_hours("", datetime(2026, 1, 1, 3, 0)) is False


# --- U85: concurrency lock --------------------------------------------------

def test_lock_excludes_concurrent_cycles(tmp_path):
    st = OperatorState(root=tmp_path)
    assert acquire_lock(st, "repo1") is True
    assert acquire_lock(st, "repo1") is False
    release_lock(st, "repo1")
    assert acquire_lock(st, "repo1") is True


def test_lock_expires_after_ttl(tmp_path):
    st = OperatorState(root=tmp_path)
    assert acquire_lock(st, "r", ttl=10, now=100.0) is True
    assert acquire_lock(st, "r", ttl=10, now=105.0) is False  # still held
    assert acquire_lock(st, "r", ttl=10, now=200.0) is True   # expired -> re-acquire


# --- U87: backpressure ------------------------------------------------------

def test_backpressure_when_approvals_pile_up(tmp_path):
    st = OperatorState(root=tmp_path)
    assert backpressure_ok(st, max_pending=2) is True
    queue = ApprovalQueue(st)
    for i in range(3):
        intent = Intent(opportunity=Opportunity(id=f"o{i}", kind="announce", workstream="promote", score=1.0))
        queue.enqueue(make_proposal(intent, proposal_id=f"p{i}", generate=lambda i, c: [{"action_class": "post_external"}]))
    assert backpressure_ok(st, max_pending=2) is False


# --- U81: continuous run loop ----------------------------------------------

def test_run_continuous_invokes_run_once_each_iteration(tmp_path):
    st = OperatorState(root=tmp_path)
    calls = []
    out = run_continuous(
        _cfg(), st,
        run_once=lambda: calls.append(1),
        iterations=3,
        clock=lambda: datetime(2026, 1, 1, 12, 0),
        sleep_fn=lambda s: None,
    )
    assert len(calls) == 3
    assert all(o["status"] == "ran" for o in out)


def test_run_continuous_skips_during_quiet_hours(tmp_path):
    st = OperatorState(root=tmp_path)
    cfg = _cfg()
    cfg.approval.quiet_hours = "00:00-23:59"  # always quiet
    calls = []
    out = run_continuous(
        cfg, st,
        run_once=lambda: calls.append(1),
        iterations=2,
        clock=lambda: datetime(2026, 1, 1, 12, 0),
        sleep_fn=lambda s: None,
    )
    assert calls == []
    assert all(o["status"] == "quiet" for o in out)
