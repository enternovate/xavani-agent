# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for real promote effectors (v0.7.0 operator U68/U72/U77)."""

from __future__ import annotations

from xavani_operator.config import ProductConfig, ProductInfo
from xavani_operator.state import OperatorState
from xavani_operator.types import PlanStep, Tier
from xavani_operator.workstreams.promote_effectors import (
    RateLimiter,
    post_effector,
    publish_effector,
    stage_content_effector,
    tool_promote_effectors,
)


def _cfg(**kw):
    return ProductConfig(product=ProductInfo(name="Acme"), **kw)


def _step(action_class, **payload):
    return PlanStep(id="s", action_class=action_class, tier=Tier.APPROVE, summary="launch v1", payload=payload)


# --- stage content (content seam + variant select + safety) ----------------

def test_stage_content_default_drafts_on_brand():
    ctx = {}
    result = stage_content_effector(config=_cfg())(_step("stage_content"), ctx)
    assert result.ok is True
    assert "Acme" in result.output
    assert ctx.get("content")  # handed to the post step


def test_stage_content_uses_agent_and_selects_brand_variant():
    cfg = _cfg()
    cfg.brand.dos = ["clear"]
    cfg.brand.donts = ["hype"]
    ctx = {}
    agent = lambda brief: ["pure hype", "a clear launch note"]
    stage_content_effector(config=cfg, content_agent=agent)(_step("stage_content"), ctx)
    assert "clear launch note" in ctx["content"]


def test_stage_content_blocks_unsafe_content():
    cfg = _cfg()
    cfg.brand.donts = ["hype"]
    result = stage_content_effector(config=cfg, content_agent=lambda b: ["all hype"])(_step("stage_content"), {})
    assert result.ok is False


# --- post (injected sender + safety + rate limit) --------------------------

def test_post_effector_posts_via_sender():
    sent = []
    result = post_effector(sender=lambda ch, txt: sent.append((ch, txt)))(
        _step("post_external", channel="x"), {"content": "hello world"}
    )
    assert result.ok is True
    assert sent == [("x", "hello world")]


def test_post_effector_without_sender_is_unwired():
    result = post_effector(sender=None)(_step("post_external", channel="x", content="hi"), {})
    assert result.ok is False


# --- U77: rate limiting -----------------------------------------------------

def test_rate_limiter_blocks_after_cap(tmp_path):
    rl = RateLimiter(OperatorState(root=tmp_path), per_day=2)
    assert rl.consume("x") is True
    assert rl.consume("x") is True
    assert rl.consume("x") is False


def test_post_effector_respects_rate_limit(tmp_path):
    sent = []
    rl = RateLimiter(OperatorState(root=tmp_path), per_day=1)
    eff = post_effector(sender=lambda ch, txt: sent.append(txt), rate_limiter=rl)
    assert eff(_step("post_external", channel="x", content="a"), {}).ok is True
    assert eff(_step("post_external", channel="x", content="b"), {}).ok is False


# --- U72: publish -----------------------------------------------------------

def test_publish_effector_writes_artifact(tmp_path):
    result = publish_effector(str(tmp_path))(_step("publish", content="# Release notes"), {})
    assert result.ok is True
    assert any(tmp_path.iterdir())


# --- assembly ---------------------------------------------------------------

def test_tool_promote_effectors_assemble(tmp_path):
    eff = tool_promote_effectors(_cfg(), state=OperatorState(root=tmp_path))
    for action in ["stage_content", "post_external", "publish"]:
        assert action in eff
