# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Promote workstream — the growth pack (v0.7.0 operator U65–U70/U74).

The other half of "build + promote": detect when there's something worth saying
(a release, a cadence due, a notable change), draft **on-brand** content, and
post it across the configured channels — always **approval-gated** (posting is
Tier 2). Like the build pack, content *generation* is an injected seam and the
channel *posting* is an injected effector; everything else is deterministic (R10):

* ``brand_context`` renders the brand voice/tone/dos-donts for the generator.
* ``select_variant`` picks the best A/B variant **deterministically** (no LLM to
  choose) — scoring by brand dos/donts.
* ``check_brand_safety`` is the gate before anything goes out (empty / off-brand).
"""

from __future__ import annotations

from typing import Any, Callable

from xavani_operator.opportunities import promote_opportunities
from xavani_operator.propose import make_proposal
from xavani_operator.types import StepResult, Verdict
from xavani_operator.verify import verify_step_results
from xavani_operator.workstreams.base import register_workstream

_PROMOTE_ACTIONS = ["stage_content", "post_external", "publish", "schedule"]


def brand_context(config: Any, subject: str = "") -> str:
    """Render the brand voice/guardrails + channels for the content generator."""
    brand = config.brand
    lines = [f"Promote: {config.product.name}"]
    if subject:
        lines.append(f"About: {subject}")
    if brand.voice:
        lines.append(f"Voice: {brand.voice}")
    if brand.tone:
        lines.append(f"Tone: {brand.tone}")
    if brand.dos:
        lines.append(f"Do: {', '.join(brand.dos)}")
    if brand.donts:
        lines.append(f"Avoid: {', '.join(brand.donts)}")
    channels = [c.platform for c in config.channels]
    if channels:
        lines.append(f"Channels: {', '.join(channels)}")
    lines.append("Write original, on-brand content; honour the voice; no hype, no clickbait.")
    return "\n".join(lines)


def check_brand_safety(text: str, config: Any) -> Verdict:
    """Deterministic gate before any outward post (empty / off-brand)."""
    if not text or not text.strip():
        return Verdict.fail("empty content")
    low = text.lower()
    bad = [d for d in config.brand.donts if d and d.lower() in low]
    if bad:
        return Verdict.fail(f"violates brand don'ts: {', '.join(bad)}")
    return Verdict.ok_()


def _variant_score(variant: str, config: Any) -> int:
    low = variant.lower()
    score = sum(1 for d in config.brand.dos if d and d.lower() in low)
    score -= 100 * sum(1 for d in config.brand.donts if d and d.lower() in low)
    return score


def select_variant(variants: list[str], config: Any) -> str:
    """Deterministically pick the best A/B variant (brand-fit; stable tie-break)."""
    if not variants:
        return ""
    best = max(range(len(variants)), key=lambda i: (_variant_score(variants[i], config), -i))
    return variants[best]


class PromoteWorkstream:
    """Growth workstream implementing the :class:`Workstream` protocol."""

    name = "promote"

    def detect_opportunities(self, perception: Any, config: Any) -> list:
        return promote_opportunities(perception, config)

    def make_plan(self, intent: Any, ctx: dict | None = None, *, generate: Callable | None = None):
        proposal = make_proposal(intent, ctx=ctx, generate=generate)
        config = (ctx or {}).get("config")
        if config is not None:
            proposal.notes = brand_context(config, intent.opportunity.rationale)
        return proposal

    def execute(self, step: Any, ctx: Any) -> StepResult:
        return StepResult(step_id=step.id, ok=False, error="run via promote_handlers(effectors) in the loop")

    def verify(self, result: Any, ctx: Any = None):
        results = result if isinstance(result, list) else [result]
        return verify_step_results(results)


def promote_handlers(effectors: dict[str, Callable] | None = None) -> dict[str, Callable]:
    """Map every promote action to a handler dispatching to an injected effector."""
    effectors = effectors or {}

    def _make(action: str) -> Callable:
        def handler(step, ctx) -> StepResult:
            fn = effectors.get(action)
            if fn is None:
                return StepResult(step_id=step.id, ok=False, error=f"'{action}' channel not wired (provide an effector)")
            out = fn(step, ctx)
            return out if isinstance(out, StepResult) else StepResult(step_id=step.id, ok=True, output=str(out))

        return handler

    return {action: _make(action) for action in _PROMOTE_ACTIONS}


def register() -> None:
    """Register the promote workstream with the operator registry."""
    register_workstream(PromoteWorkstream())
