# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""End-to-end single-cycle tests for the operator loop (v0.7.0 operator U47–U49)."""

from __future__ import annotations

from xavani_operator.approval_queue import ApprovalQueue
from xavani_operator.config import Channel, Goal, ProductConfig, ProductInfo
from xavani_operator.learn import get_weight
from xavani_operator.loop import default_handlers, last_checkpoint, run_cycle
from xavani_operator.state import OperatorState
from xavani_operator.types import ProposalStatus, StepResult


def _fix_tests_repo(tmp_path):
    """A directory whose pytest cache shows a failing test (→ fix_tests opportunity)."""
    repo = tmp_path / "repo"
    cache = repo / ".pytest_cache" / "v" / "cache"
    cache.mkdir(parents=True)
    (cache / "lastfailed").write_text('{"tests/test_x.py::test_a": true}')
    return repo


def test_run_cycle_executes_approved_safe_plan_end_to_end(tmp_path):
    cfg = ProductConfig(product=ProductInfo(name="X", repo=str(_fix_tests_repo(tmp_path))))
    state = OperatorState(root=tmp_path / "op")
    sent = []

    def ok_handler(step, ctx):
        return StepResult(step_id=step.id, ok=True, output="done")

    handlers = {
        ac: ok_handler
        for ac in ["analyze", "draft_staging", "run_tests", "commit_workbranch", "open_draft_pr"]
    }
    report = run_cycle(cfg, state, handlers=handlers, sender=sent.append)

    assert report.executed >= 1          # the plan ran
    assert report.verified == 1          # verification passed
    assert get_weight(state, "fix_tests") > 1.0  # learn fed back
    assert sent                          # report was delivered


def test_run_cycle_no_opportunities_is_a_noop(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    cfg = ProductConfig(product=ProductInfo(name="X", repo=str(empty)))
    report = run_cycle(cfg, OperatorState(root=tmp_path / "op"))
    assert report.executed == 0
    assert "no opportunities" in report.notes.lower()


def test_run_cycle_pending_when_outward_step_and_no_approver(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    # A channel makes the top opportunity 'cadence_content', whose plan posts externally (Tier 2).
    cfg = ProductConfig(
        product=ProductInfo(name="X", repo=str(empty)),
        channels=[Channel(platform="x")],
    )
    state = OperatorState(root=tmp_path / "op")
    report = run_cycle(cfg, state)
    assert report.executed == 0
    assert "pending" in report.notes.lower()
    assert ApprovalQueue(state).list(ProposalStatus.PENDING)  # left queued for the human


def test_run_cycle_approver_can_authorize_outward_plan(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    cfg = ProductConfig(
        product=ProductInfo(name="X", repo=str(empty)),
        channels=[Channel(platform="x")],
    )
    state = OperatorState(root=tmp_path / "op")
    handlers = {ac: (lambda s, c: StepResult(step_id=s.id, ok=True)) for ac in ["stage_content", "post_external"]}
    report = run_cycle(cfg, state, handlers=handlers, approver=lambda p: True)
    assert report.executed >= 1
    assert report.verified == 1


def test_checkpoint_written_each_cycle(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    cfg = ProductConfig(product=ProductInfo(name="X", repo=str(empty)))
    state = OperatorState(root=tmp_path / "op")
    run_cycle(cfg, state, cycle_id="cycle-1")
    cp = last_checkpoint(state)
    assert cp is not None
    assert cp["cycle_id"] == "cycle-1"


def test_default_handlers_cover_safe_actions():
    h = default_handlers()
    assert "analyze" in h
    assert "post_external" not in h  # outward actions need real, gated handlers (M4/M5)


def test_run_cycle_uses_registered_workstream_taste(tmp_path):
    from xavani_operator.approval_queue import ApprovalQueue
    from xavani_operator.workstreams.base import clear_workstreams
    from xavani_operator.workstreams.build import register as register_build

    clear_workstreams()
    register_build()
    try:
        empty = tmp_path / "empty"
        empty.mkdir()
        cfg = ProductConfig(
            product=ProductInfo(name="X", repo=str(empty), stack=["react"]),
            goals=[Goal(id="g1", intent="ship a landing page website", priority=1)],
        )
        state = OperatorState(root=tmp_path / "op")
        run_cycle(cfg, state)
        # The plan should carry the learned design taste (build workstream wired in).
        proposals = ApprovalQueue(state).list()
        assert proposals
        assert any("Design direction" in (p.notes or "") for p in proposals)
    finally:
        clear_workstreams()
