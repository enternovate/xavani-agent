# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for verify / report / learn (v0.7.0 operator U40–U46)."""

from __future__ import annotations

from xavani_operator.config import ProductConfig, ProductInfo
from xavani_operator.learn import get_weight, record_outcome, update_weight
from xavani_operator.propose import make_proposal
from xavani_operator.report import build_cycle_report, deliver_report, render_report
from xavani_operator.state import OperatorState
from xavani_operator.types import CycleReport, Intent, Opportunity, StepResult, Verdict
from xavani_operator.verify import check_content_policy, run_checks, verify_step_results


def _proposal(action_classes=("analyze", "run_tests")):
    def gen(intent, ctx):
        return [{"action_class": ac, "summary": ac} for ac in action_classes]

    intent = Intent(opportunity=Opportunity(id="o", kind="fix_tests", workstream="build", score=1.0))
    return make_proposal(intent, proposal_id="p1", generate=gen)


# --- U40: verify ------------------------------------------------------------

def test_verify_results_ok_when_all_ok():
    assert verify_step_results([StepResult("s", ok=True)]).ok is True


def test_verify_results_fails_on_error():
    v = verify_step_results([StepResult("s", ok=False, error="boom")])
    assert v.ok is False
    assert "boom" in v.findings[0]


def test_run_checks_aggregates_verdicts():
    v = run_checks([lambda c: Verdict.ok_(), lambda c: Verdict.fail("nope")])
    assert v.ok is False
    assert "nope" in v.findings


def test_run_checks_accepts_tuple_form():
    v = run_checks([lambda c: (True, "ok"), lambda c: (False, "bad")])
    assert v.ok is False
    assert "bad" in v.findings


# --- U41: content/brand policy ---------------------------------------------

def test_content_policy_flags_brand_donts():
    cfg = ProductConfig(product=ProductInfo(name="X"))
    cfg.brand.donts = ["hype"]
    assert check_content_policy("lots of hype here", cfg).ok is False
    assert check_content_policy("clear, honest copy", cfg).ok is True


# --- U43/U44: report --------------------------------------------------------

def test_build_report_counts_executed_and_verified():
    results = [StepResult("s0", ok=True), StepResult("s1", ok=True)]
    report = build_cycle_report("c1", _proposal(), results, Verdict.ok_())
    assert report.cycle_id == "c1"
    assert report.executed == 2
    assert report.verified == 1


def test_render_report_contains_summary():
    report = build_cycle_report("c1", _proposal(), [StepResult("s0", ok=True)], Verdict.ok_())
    text = render_report(report)
    assert "c1" in text


def test_deliver_report_uses_sender():
    sent = []
    report = build_cycle_report("c1", _proposal(), [StepResult("s0", ok=True)], Verdict.ok_())
    assert deliver_report(report, sender=sent.append) is True
    assert sent
    assert deliver_report(report) is False


# --- U45/U46: learn ---------------------------------------------------------

def test_weight_defaults_to_one(tmp_path):
    assert get_weight(OperatorState(root=tmp_path), "fix_tests") == 1.0


def test_weight_rises_on_success_falls_on_failure(tmp_path):
    st = OperatorState(root=tmp_path)
    up = update_weight(st, "fix_tests", True)
    assert up > 1.0
    down = update_weight(st, "fix_tests", False)
    assert down < up


def test_record_outcome_persists_cycle_and_weight(tmp_path):
    st = OperatorState(root=tmp_path)
    record_outcome(st, CycleReport(cycle_id="c1", executed=2, verified=1), "fix_tests", True)
    assert st.get("cycles", "c1")["kind"] == "fix_tests"
    assert get_weight(st, "fix_tests") > 1.0
