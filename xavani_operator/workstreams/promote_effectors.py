# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Real promote effectors — channels + safety + rate limits (v0.7.0 operator U68/U72/U77).

Production effectors for the promote workstream:

* ``stage_content_effector`` — draft on-brand content via an injected
  ``content_agent`` (the app wires the LLM); deterministically pick the best A/B
  variant and **gate it through brand safety** before it can be posted.
* ``post_effector`` — post via an injected ``sender(channel, text)`` (the app
  wires ``gateway/send_message_tool``), re-checking safety and honouring a
  per-channel :class:`RateLimiter`. Posting is Tier 2 (approval-gated upstream).
* ``publish_effector`` — write a real published artifact (changelog/blog).

Content generation and channel sending are the only model/network surfaces, and
both are injected — selection, safety, and rate limiting are deterministic (R10).
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any, Callable

from xavani_operator.types import StepResult
from xavani_operator.workstreams.promote import brand_context, check_brand_safety, select_variant


def _content(step: Any, ctx: Any) -> str:
    if isinstance(ctx, dict) and ctx.get("content"):
        return ctx["content"]
    return step.payload.get("content") or step.summary or ""


def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", name) or "channel"


class RateLimiter:
    """Per-channel, per-day post cap backed by the operator state store (U77)."""

    def __init__(self, state: Any, per_day: int = 10) -> None:
        self.state = state
        self.per_day = per_day

    def consume(self, channel: str, day: str | None = None) -> bool:
        """Reserve one post for ``channel`` today; ``False`` if the cap is hit."""
        key = f"{_safe(channel)}.{day or date.today().strftime('%Y%m%d')}"
        rec = self.state.get("rate", key) or {"channel": channel, "count": 0}
        if rec["count"] >= self.per_day:
            return False
        rec["count"] += 1
        self.state.put("rate", key, rec)
        return True


def stage_content_effector(config: Any = None, content_agent: Callable[[str], Any] | None = None) -> Callable:
    """Draft + variant-select + safety-gate content; hand it to the post step via ctx."""

    def effector(step, ctx) -> StepResult:
        subject = step.summary
        brief = brand_context(config, subject) if config is not None else subject
        if content_agent is not None:
            variants = content_agent(brief)
            variants = variants if isinstance(variants, list) else [str(variants)]
        else:
            name = config.product.name if config is not None else "Update"
            variants = [f"{name}: {subject}".strip()]
        chosen = select_variant(variants, config) if config is not None else (variants[0] if variants else "")
        if config is not None:
            verdict = check_brand_safety(chosen, config)
            if not verdict.ok:
                return StepResult(step_id=step.id, ok=False, error=verdict.findings[0])
        if isinstance(ctx, dict):
            ctx["content"] = chosen
        return StepResult(step_id=step.id, ok=True, output=chosen[:160])

    return effector


def post_effector(
    sender: Callable[[str, str], Any] | None = None,
    rate_limiter: RateLimiter | None = None,
    config: Any = None,
) -> Callable:
    """Post content to a channel via an injected ``sender`` (safety + rate gated)."""

    def effector(step, ctx) -> StepResult:
        content = _content(step, ctx)
        channel = step.payload.get("channel", "default")
        if config is not None:
            verdict = check_brand_safety(content, config)
            if not verdict.ok:
                return StepResult(step_id=step.id, ok=False, error=verdict.findings[0])
        if sender is None:
            return StepResult(step_id=step.id, ok=False, error="no channel sender wired (provide a sender)")
        if rate_limiter is not None and not rate_limiter.consume(channel):
            return StepResult(step_id=step.id, ok=False, error=f"rate limit reached for {channel}")
        sender(channel, content)
        return StepResult(step_id=step.id, ok=True, output=f"posted to {channel}")

    return effector


def publish_effector(repo: str) -> Callable:
    """Write content as a real published artifact (changelog/blog)."""

    def effector(step, ctx) -> StepResult:
        content = _content(step, ctx)
        if not content.strip():
            return StepResult(step_id=step.id, ok=False, error="nothing to publish")
        out_dir = Path(repo) / "published"
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            path = out_dir / "latest.md"
            path.write_text(content, encoding="utf-8")
        except OSError as exc:
            return StepResult(step_id=step.id, ok=False, error=str(exc))
        return StepResult(step_id=step.id, ok=True, output=f"published to {path}")

    return effector


def _schedule_effector(step, ctx) -> StepResult:
    return StepResult(step_id=step.id, ok=True, output=f"[scheduled] {step.summary}")


def tool_promote_effectors(
    config: Any,
    *,
    content_agent: Callable[[str], Any] | None = None,
    sender: Callable[[str, str], Any] | None = None,
    state: Any = None,
    per_day: int = 10,
) -> dict[str, Callable]:
    """Assemble the full promote effector set."""
    rate_limiter = RateLimiter(state, per_day) if state is not None else None
    return {
        "stage_content": stage_content_effector(config=config, content_agent=content_agent),
        "post_external": post_effector(sender=sender, rate_limiter=rate_limiter, config=config),
        "publish": publish_effector(config.product.repo or "."),
        "schedule": _schedule_effector,
    }
