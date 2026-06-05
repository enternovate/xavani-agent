# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Propose: turn an Intent into a concrete, tier-tagged plan (v0.7.0 operator U23/U24/U33).

This is the **one place the LLM is allowed** in the operator loop — and even here
the model call is an *injectable seam* (``generate``), so:

* the default path is a deterministic **template** plan (zero cost, always works);
* the richer path injects an LLM generator (the loop wires the real client in M3);
* tests inject a fake generator and never touch a real model.

Whatever produces the raw steps, **tier assignment is deterministic** (R10): the
generator only proposes *what* to do (action classes); ``tiers.classify`` decides
*how much consent* each step needs. ``build_plan_prompt`` is the deterministic
prompt the LLM generator would send. Budget is checked here too, so we never spend
on generation past the configured ceiling.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict
from typing import Any, Callable

from xavani_operator.tiers import classify
from xavani_operator.types import Intent, Opportunity, PlanStep, Proposal, ProposalStatus, Tier

# Deterministic plan skeletons per opportunity kind: (action_class, summary).
_TEMPLATES: dict[str, list[tuple[str, str]]] = {
    "fix_tests": [
        ("analyze", "Locate the failing tests and root cause"),
        ("draft_staging", "Draft fixes on a work branch"),
        ("run_tests", "Run the test suite"),
        ("commit_workbranch", "Commit the fix"),
        ("open_draft_pr", "Open a draft PR for review"),
    ],
    "address_todos": [
        ("analyze", "Review TODO/FIXME markers"),
        ("draft_staging", "Draft the cleanups"),
        ("run_tests", "Run the test suite"),
        ("commit_workbranch", "Commit the cleanups"),
    ],
    "build_feature": [
        ("analyze", "Design the feature from the goal"),
        ("draft_staging", "Implement it on a work branch"),
        ("run_tests", "Run the test suite"),
        ("commit_workbranch", "Commit the feature"),
        ("open_draft_pr", "Open a draft PR for review"),
    ],
    "announce": [
        ("stage_content", "Draft the announcement"),
        ("post_external", "Post to the configured channels"),
    ],
    "cadence_content": [
        ("stage_content", "Draft scheduled content"),
        ("post_external", "Post to the configured channels"),
    ],
    "housekeeping": [
        ("analyze", "Review uncommitted changes"),
        ("commit_workbranch", "Commit work-in-progress to a branch"),
    ],
}
_DEFAULT_TEMPLATE = [("analyze", "Investigate and plan next steps")]


def template_generate(intent: Intent, ctx: dict | None = None) -> list[dict]:
    """Deterministic, zero-cost plan generator (the default ``generate``)."""
    tmpl = _TEMPLATES.get(intent.opportunity.kind, _DEFAULT_TEMPLATE)
    return [{"action_class": ac, "summary": summary, "payload": {}} for ac, summary in tmpl]


def build_plan_prompt(intent: Intent, config) -> str:
    """The deterministic prompt an LLM generator would send (no call made here)."""
    opp = intent.opportunity
    lines = [
        f"Product: {config.product.name}",
        f"Task: {opp.workstream}/{opp.kind} — {opp.rationale}",
        f"Brand voice: {config.brand.voice or '(unspecified)'}",
        "Produce a concrete, minimal plan as a list of steps; each step is an "
        "action_class plus a one-line summary. Use only safe, reversible actions "
        "where possible.",
    ]
    return "\n".join(lines)


def make_proposal(
    intent: Intent,
    ctx: dict | None = None,
    *,
    generate: Callable[[Intent, dict | None], list[dict]] | None = None,
    proposal_id: str | None = None,
) -> Proposal:
    """Build a :class:`Proposal` from an intent, tagging every step with its tier."""
    gen = generate or template_generate
    raw_steps = gen(intent, ctx)
    overrides = (ctx or {}).get("tier_overrides")
    pid = proposal_id or f"prop-{uuid.uuid4().hex[:12]}"
    steps: list[PlanStep] = []
    for i, rs in enumerate(raw_steps):
        action_class = rs["action_class"]
        steps.append(PlanStep(
            id=f"{pid}:s{i}",
            action_class=action_class,
            tier=classify(action_class, overrides),
            summary=rs.get("summary", ""),
            payload=rs.get("payload", {}),
        ))
    return Proposal(id=pid, intent=intent, steps=steps, status=ProposalStatus.PENDING)


def within_budget(config, usage: dict | None = None) -> bool:
    """True if a new proposal is allowed under the config budgets (0 = unlimited)."""
    usage = usage or {}
    b = config.budgets
    if b.llm_tokens_per_day and usage.get("tokens_today", 0) >= b.llm_tokens_per_day:
        return False
    if b.spend_per_day and usage.get("spend_today", 0) >= b.spend_per_day:
        return False
    if b.max_actions_per_cycle and usage.get("actions_this_cycle", 0) >= b.max_actions_per_cycle:
        return False
    return True


def proposal_to_dict(p: Proposal) -> dict[str, Any]:
    """Serialise a Proposal for the state store (JSON-safe)."""
    return {
        "id": p.id,
        "status": p.status.value,
        "created_at": p.created_at,
        "notes": p.notes,
        "intent": {"opportunity": asdict(p.intent.opportunity), "params": p.intent.params},
        "steps": [
            {
                "id": s.id,
                "action_class": s.action_class,
                "tier": int(s.tier),
                "summary": s.summary,
                "payload": s.payload,
            }
            for s in p.steps
        ],
    }


def proposal_from_dict(d: dict[str, Any]) -> Proposal:
    """Rebuild a Proposal from its stored dict."""
    opp = Opportunity(**d["intent"]["opportunity"])
    intent = Intent(opportunity=opp, params=d["intent"].get("params", {}))
    steps = [
        PlanStep(
            id=s["id"],
            action_class=s["action_class"],
            tier=Tier(s["tier"]),
            summary=s.get("summary", ""),
            payload=s.get("payload", {}),
        )
        for s in d["steps"]
    ]
    return Proposal(
        id=d["id"],
        intent=intent,
        steps=steps,
        status=ProposalStatus(d["status"]),
        created_at=d.get("created_at", 0.0),
        notes=d.get("notes", ""),
    )
