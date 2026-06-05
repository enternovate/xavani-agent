# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the Build workstream (v0.7.0 operator U51–U56) — taste-integrated."""

from __future__ import annotations

from xavani_operator.config import Goal, ProductConfig, ProductInfo
from xavani_operator.types import Intent, Opportunity, Perception, PlanStep, StepResult, Tier
from xavani_operator.workstreams.base import Workstream
from xavani_operator.workstreams.build import BuildWorkstream, build_handlers


def _intent(kind="build_feature", rationale="build a marketing landing page website"):
    return Intent(opportunity=Opportunity(id="o", kind=kind, workstream="build", score=1.0, rationale=rationale))


def _step(action_class, tier=Tier.AUTO):
    return PlanStep(id="s", action_class=action_class, tier=tier)


# --- U51: it's a workstream that detects build work ------------------------

def test_build_satisfies_workstream_protocol():
    assert isinstance(BuildWorkstream(), Workstream)


def test_detect_opportunities_surfaces_build_work():
    cfg = ProductConfig(product=ProductInfo(name="X"), goals=[Goal(id="g1", intent="ship landing page", priority=1)])
    opps = BuildWorkstream().detect_opportunities(Perception(), cfg)
    assert any(o.workstream == "build" for o in opps)


# --- U52/L9: make_plan injects the LEARNED TASTE for design work -----------

def test_make_plan_injects_learned_taste_for_a_website():
    cfg = ProductConfig(product=ProductInfo(name="X", stack=["react"]))
    proposal = BuildWorkstream().make_plan(_intent(rationale="build a landing page website"), ctx={"config": cfg})
    assert "Design direction" in proposal.notes      # taste recall injected
    assert "AVOID" in proposal.notes                 # anti-generic guardrail carried


def test_make_plan_includes_preferences_when_provided():
    cfg = ProductConfig(product=ProductInfo(name="X", stack=["react"]))
    proposal = BuildWorkstream().make_plan(
        _intent(rationale="build a website"),
        ctx={"config": cfg, "preferences": ["prefers dark editorial layouts"]},
    )
    assert "dark editorial" in proposal.notes


def test_make_plan_no_taste_for_non_design_work():
    cfg = ProductConfig(product=ProductInfo(name="X"))
    proposal = BuildWorkstream().make_plan(_intent(kind="fix_tests", rationale="fix failing tests"), ctx={"config": cfg})
    assert "Design direction" not in (proposal.notes or "")


def test_make_plan_tags_steps_with_tiers():
    cfg = ProductConfig(product=ProductInfo(name="X"))
    proposal = BuildWorkstream().make_plan(_intent(), ctx={"config": cfg})
    assert proposal.steps
    assert all(isinstance(s.tier, Tier) for s in proposal.steps)


# --- U53/U54/U59: handlers dispatch via injected effectors -----------------

def test_build_handlers_dispatch_via_injected_effector():
    called = []
    effectors = {"run_tests": lambda step, ctx: called.append("ran") or "green"}
    handlers = build_handlers(effectors)
    result = handlers["run_tests"](_step("run_tests"), None)
    assert result.ok is True
    assert called == ["ran"]


def test_build_handlers_report_unwired_effector():
    handlers = build_handlers({})
    result = handlers["deploy"](_step("deploy", Tier.APPROVE), None)
    assert result.ok is False
    assert "wired" in result.error.lower()


def test_build_handlers_cover_full_stack_actions():
    handlers = build_handlers({})
    for action in ["implement_backend", "implement_frontend", "migrate", "open_draft_pr", "deploy"]:
        assert action in handlers


# --- U56: verify ------------------------------------------------------------

def test_verify_passes_for_successful_results():
    assert BuildWorkstream().verify([StepResult("s", ok=True)], None).ok is True


def test_verify_fails_on_error():
    assert BuildWorkstream().verify([StepResult("s", ok=False, error="x")], None).ok is False


# --- U53: local effectors (safe, real glue) --------------------------------

def test_local_effectors_include_safe_actions():
    from xavani_operator.workstreams.build import local_build_effectors

    eff = local_build_effectors(".")
    for action in ["analyze", "draft_staging", "run_tests", "commit_workbranch"]:
        assert action in eff


def test_local_analyze_effector_is_a_safe_note():
    from xavani_operator.workstreams.build import local_build_effectors

    result = local_build_effectors(".")["analyze"](_step("analyze"), None)
    assert result.ok is True
