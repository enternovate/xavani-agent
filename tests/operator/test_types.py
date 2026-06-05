# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the Xavani Operator core types (v0.7.0 operator U1)."""

from __future__ import annotations

from xavani_operator.types import (
    CycleReport,
    Intent,
    Opportunity,
    PlanStep,
    Proposal,
    ProposalStatus,
    StepResult,
    Tier,
    Verdict,
)


def test_tier_is_ordered_intenum():
    assert int(Tier.AUTO) == 0
    assert int(Tier.NOTIFY) == 1
    assert int(Tier.APPROVE) == 2
    assert int(Tier.BLOCK) == 3
    # Ordering is meaningful: higher tier = more restrictive.
    assert Tier.AUTO < Tier.APPROVE < Tier.BLOCK


def test_verdict_ok_helper_has_no_findings():
    v = Verdict.ok_()
    assert v.ok is True
    assert v.findings == []


def test_verdict_fail_helper_records_reason():
    v = Verdict.fail("tests failed")
    assert v.ok is False
    assert "tests failed" in v.findings


def test_opportunity_sorts_by_score_descending():
    a = Opportunity(id="a", kind="fix", workstream="build", score=0.2, rationale="")
    b = Opportunity(id="b", kind="fix", workstream="build", score=0.9, rationale="")
    c = Opportunity(id="c", kind="fix", workstream="build", score=0.5, rationale="")
    ranked = sorted([a, b, c], key=lambda o: o.score, reverse=True)
    assert [o.id for o in ranked] == ["b", "c", "a"]


def test_plan_step_carries_action_class_and_tier():
    step = PlanStep(id="s1", action_class="post_external", tier=Tier.APPROVE, summary="post launch")
    assert step.action_class == "post_external"
    assert step.tier == Tier.APPROVE


def test_proposal_defaults_to_pending_status():
    intent = Intent(opportunity=Opportunity(id="o", kind="fix", workstream="build", score=1.0, rationale=""))
    proposal = Proposal(id="p1", intent=intent, steps=[])
    assert proposal.status == ProposalStatus.PENDING


def test_step_result_marks_success_and_failure():
    ok = StepResult(step_id="s1", ok=True, output="done")
    bad = StepResult(step_id="s2", ok=False, error="boom")
    assert ok.ok and ok.output == "done"
    assert not bad.ok and bad.error == "boom"


def test_cycle_report_counts_render():
    report = CycleReport(cycle_id="c1", proposed=2, approved=1, executed=1, verified=1)
    assert report.proposed == 2
    assert report.cycle_id == "c1"
