# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for propose: the (injectable) LLM generation seam (v0.7.0 operator U23/U24/U33)."""

from __future__ import annotations

from xavani_operator.config import Budgets, ProductConfig, ProductInfo
from xavani_operator.propose import (
    build_plan_prompt,
    make_proposal,
    proposal_from_dict,
    proposal_to_dict,
    template_generate,
    within_budget,
)
from xavani_operator.types import Intent, Opportunity, ProposalStatus, Tier


def _intent(kind="fix_tests") -> Intent:
    return Intent(opportunity=Opportunity(id="o", kind=kind, workstream="build", score=1.0, rationale="why"))


# --- U23: generation + tier tagging ----------------------------------------

def test_template_generate_for_fix_tests():
    classes = [s["action_class"] for s in template_generate(_intent("fix_tests"))]
    assert "run_tests" in classes
    assert "open_draft_pr" in classes


def test_make_proposal_tags_each_step_with_a_tier():
    p = make_proposal(_intent("announce"), proposal_id="p1")
    tiers = {s.action_class: s.tier for s in p.steps}
    assert tiers["post_external"] == Tier.APPROVE
    assert tiers["stage_content"] == Tier.NOTIFY


def test_make_proposal_uses_injected_generator_no_real_llm():
    def fake_gen(intent, ctx):
        return [{"action_class": "deploy", "summary": "ship it"}]

    p = make_proposal(_intent(), proposal_id="p1", generate=fake_gen)
    assert len(p.steps) == 1
    assert p.steps[0].action_class == "deploy"
    assert p.steps[0].tier == Tier.APPROVE  # deterministically classified


def test_make_proposal_applies_config_tier_overrides():
    p = make_proposal(_intent("announce"), ctx={"tier_overrides": {"post_external": 1}}, proposal_id="p1")
    post = next(s for s in p.steps if s.action_class == "post_external")
    assert post.tier == Tier.NOTIFY


def test_make_proposal_starts_pending():
    assert make_proposal(_intent(), proposal_id="p1").status == ProposalStatus.PENDING


def test_build_plan_prompt_includes_context():
    cfg = ProductConfig(product=ProductInfo(name="Acme"))
    cfg.brand.voice = "playful"
    prompt = build_plan_prompt(_intent("announce"), cfg)
    assert "Acme" in prompt
    assert "announce" in prompt
    assert "playful" in prompt


# --- U24: serialization round-trip -----------------------------------------

def test_proposal_round_trips_through_dict():
    p = make_proposal(_intent("announce"), proposal_id="p1")
    restored = proposal_from_dict(proposal_to_dict(p))
    assert restored.id == p.id
    assert [s.action_class for s in restored.steps] == [s.action_class for s in p.steps]
    assert restored.steps[0].tier == p.steps[0].tier
    assert restored.status == p.status
    assert restored.intent.opportunity.kind == "announce"


# --- U33: budget guard ------------------------------------------------------

def test_within_budget_blocks_when_action_cap_hit():
    cfg = ProductConfig(product=ProductInfo(name="X"), budgets=Budgets(max_actions_per_cycle=2))
    assert within_budget(cfg, {"actions_this_cycle": 1}) is True
    assert within_budget(cfg, {"actions_this_cycle": 2}) is False


def test_within_budget_zero_means_unlimited():
    cfg = ProductConfig(product=ProductInfo(name="X"), budgets=Budgets(llm_tokens_per_day=0))
    assert within_budget(cfg, {"tokens_today": 10_000_000}) is True
