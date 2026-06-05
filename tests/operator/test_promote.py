# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the Promote workstream (v0.7.0 operator U65–U70/U74)."""

from __future__ import annotations

from xavani_operator.config import Channel, ProductConfig, ProductInfo
from xavani_operator.types import Intent, Opportunity, Perception, PlanStep, StepResult, Tier
from xavani_operator.workstreams.base import Workstream
from xavani_operator.workstreams.promote import (
    PromoteWorkstream,
    brand_context,
    check_brand_safety,
    promote_handlers,
    select_variant,
)


def _intent(kind="announce", rationale="announce the v1 launch"):
    return Intent(opportunity=Opportunity(id="o", kind=kind, workstream="promote", score=0.6, rationale=rationale))


def _cfg(**kw):
    return ProductConfig(product=ProductInfo(name="Acme"), **kw)


def _step(action_class="post_external", tier=Tier.APPROVE):
    return PlanStep(id="s", action_class=action_class, tier=tier)


# --- U65: detection ---------------------------------------------------------

def test_promote_satisfies_workstream_protocol():
    assert isinstance(PromoteWorkstream(), Workstream)


def test_detect_opportunities_surfaces_promote_work():
    cfg = _cfg(channels=[Channel(platform="x")])
    opps = PromoteWorkstream().detect_opportunities(Perception(), cfg)
    assert any(o.workstream == "promote" for o in opps)


# --- U66: make_plan carries brand voice ------------------------------------

def test_make_plan_attaches_brand_voice():
    cfg = _cfg()
    cfg.brand.voice = "warm and witty"
    proposal = PromoteWorkstream().make_plan(_intent(), ctx={"config": cfg})
    assert "warm and witty" in proposal.notes


def test_make_plan_tags_external_post_as_approve():
    proposal = PromoteWorkstream().make_plan(_intent(), ctx={"config": _cfg()})
    tiers = {s.action_class: s.tier for s in proposal.steps}
    assert tiers.get("post_external") == Tier.APPROVE  # outward posting always gated


# --- U70: brand / safety gate ----------------------------------------------

def test_check_brand_safety_flags_donts():
    cfg = _cfg()
    cfg.brand.donts = ["hype"]
    assert check_brand_safety("so much hype!!!", cfg).ok is False
    assert check_brand_safety("a clear, honest update", cfg).ok is True


def test_check_brand_safety_rejects_empty():
    assert check_brand_safety("   ", _cfg()).ok is False


# --- U74: deterministic A/B variant selection ------------------------------

def test_select_variant_prefers_brand_dos_avoids_donts():
    cfg = _cfg()
    cfg.brand.dos = ["clear"]
    cfg.brand.donts = ["hype"]
    assert select_variant(["lots of hype", "a clear update", "ok"], cfg) == "a clear update"


def test_select_variant_is_deterministic():
    cfg = _cfg()
    variants = ["alpha", "beta", "gamma"]
    assert select_variant(variants, cfg) == select_variant(variants, cfg)


def test_select_variant_empty_is_empty():
    assert select_variant([], _cfg()) == ""


# --- U68: handlers dispatch via injected channel effectors -----------------

def test_promote_handlers_dispatch_via_effector():
    called = []
    handlers = promote_handlers({"post_external": lambda s, c: called.append("posted") or StepResult(s.id, ok=True)})
    result = handlers["post_external"](_step(), None)
    assert result.ok is True
    assert called == ["posted"]


def test_promote_handlers_report_unwired_channel():
    result = promote_handlers({})["post_external"](_step(), None)
    assert result.ok is False
    assert "wired" in result.error.lower()


def test_verify_passes_for_ok_results():
    assert PromoteWorkstream().verify([StepResult("s", ok=True)], None).ok is True
