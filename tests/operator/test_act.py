# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the plan executor / dispatcher (v0.7.0 operator U37/U39)."""

from __future__ import annotations

from xavani_operator.act import execute_plan
from xavani_operator.propose import make_proposal
from xavani_operator.types import Intent, Opportunity, StepResult


def _proposal(action_classes, pid="p1"):
    def gen(intent, ctx):
        return [{"action_class": ac, "summary": ac} for ac in action_classes]

    intent = Intent(opportunity=Opportunity(id="o", kind="k", workstream="build", score=1.0))
    return make_proposal(intent, proposal_id=pid, generate=gen)


def test_executes_each_step_with_its_handler():
    ran = []

    def h(step, ctx):
        ran.append(step.action_class)
        return StepResult(step_id=step.id, ok=True, output="ok")

    res = execute_plan(_proposal(["analyze", "run_tests"]), {"analyze": h, "run_tests": h})
    assert [r.ok for r in res] == [True, True]
    assert ran == ["analyze", "run_tests"]


def test_handler_returning_plain_value_is_wrapped_ok():
    res = execute_plan(_proposal(["analyze"]), {"analyze": lambda s, c: "did it"})
    assert res[0].ok is True
    assert "did it" in res[0].output


def test_missing_handler_fails_and_stops():
    handlers = {"analyze": lambda s, c: StepResult(step_id=s.id, ok=True)}
    res = execute_plan(_proposal(["analyze", "deploy", "run_tests"]), handlers)
    assert len(res) == 2  # stopped at 'deploy' (no handler); 'run_tests' never reached
    assert res[0].ok is True
    assert res[1].ok is False
    assert "handler" in res[1].error.lower()


def test_exception_in_handler_stops():
    def boom(step, ctx):
        raise RuntimeError("kaboom")

    res = execute_plan(_proposal(["analyze", "run_tests"]), {"analyze": boom})
    assert len(res) == 1
    assert res[0].ok is False
    assert "kaboom" in res[0].error


def test_tier3_block_requires_reconfirm():
    handlers = {"force_push": lambda s, c: StepResult(step_id=s.id, ok=True)}
    declined = execute_plan(_proposal(["force_push"]), handlers, reconfirm=lambda step: False)
    assert declined[0].ok is False
    assert "declin" in declined[0].error.lower()
    approved = execute_plan(_proposal(["force_push"]), handlers, reconfirm=lambda step: True)
    assert approved[0].ok is True


def test_stops_on_first_failed_result():
    handlers = {
        "analyze": lambda s, c: StepResult(step_id=s.id, ok=False, error="bad"),
        "run_tests": lambda s, c: StepResult(step_id=s.id, ok=True),
    }
    res = execute_plan(_proposal(["analyze", "run_tests"]), handlers)
    assert len(res) == 1
    assert res[0].ok is False
