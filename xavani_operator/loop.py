# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""The operator control loop (v0.7.0 operator U47/U48).

``run_cycle`` wires the whole OODA loop for one pass:

    perceive → opportunities (× learned weights) → decide → propose →
    [tiered gate] → act → verify → (rollback on failure) → report → learn

Every decision step is deterministic (R10); the only model use is the injected
``generate`` passed to ``propose``. Generation, execution handlers, the approver,
tier-3 reconfirm, the report sender, and rollback are all **injected**, so the
loop is fully testable with fakes and the CLI/M4+ wire real ones. A checkpoint is
written each cycle (fuller mid-cycle resume arrives with the durability engine in
M6).
"""

from __future__ import annotations

import uuid
from typing import Any, Callable

from xavani_operator.act import execute_plan
from xavani_operator.approval_queue import ApprovalQueue, gate
from xavani_operator.audit import AuditLog
from xavani_operator.decide import decide
from xavani_operator.learn import get_weight, record_outcome
from xavani_operator.opportunities import detect
from xavani_operator.perceive import perceive
from xavani_operator.propose import make_proposal
from xavani_operator.report import build_cycle_report, deliver_report
from xavani_operator.types import CycleReport, ProposalStatus, StepResult
from xavani_operator.verify import verify_step_results
from xavani_operator.workstreams.base import get_workstream

# Safe Tier-0/1 actions the bare loop can run on its own. Outward/destructive
# actions (post_external, deploy, force_push, …) intentionally have NO default
# handler — they need the real, gated handlers the build/promote packs add (M4/M5).
_SAFE_DEFAULT_ACTIONS = [
    "read", "analyze", "lint", "run_tests", "draft_staging",
    "commit_workbranch", "open_draft_pr", "stage_content", "create_issue",
]


def default_handlers() -> dict[str, Callable]:
    """Labeled, safe stub handlers for Tier-0/1 actions (real ones land in M4/M5)."""

    def _make(action: str) -> Callable:
        def handler(step, ctx) -> StepResult:
            return StepResult(step_id=step.id, ok=True, output=f"[m3-stub] {action}: {step.summary}")

        return handler

    return {action: _make(action) for action in _SAFE_DEFAULT_ACTIONS}


def run_cycle(
    config,
    state,
    *,
    generate: Callable | None = None,
    handlers: dict[str, Callable] | None = None,
    approver: Callable | None = None,
    reconfirm: Callable | None = None,
    sender: Callable[[str], object] | None = None,
    rollback: Callable[[], object] | None = None,
    cycle_id: str | None = None,
) -> CycleReport:
    """Run one full operator cycle; return its :class:`CycleReport`."""
    cid = cycle_id or f"cycle-{uuid.uuid4().hex[:12]}"

    # Perceive → opportunities, weighted by what we've learned works (U46 closure).
    perception = perceive(config, state)
    opportunities = detect(perception, config)
    for opp in opportunities:
        opp.score = round(opp.score * get_weight(state, opp.kind), 6)
    opportunities.sort(key=lambda o: (-o.score, o.id))

    intent = decide(opportunities, config)
    if intent is None:
        report = CycleReport(cycle_id=cid, notes="no opportunities — nothing to do")
        _finish(state, report, sender)
        return report

    # Propose (the one LLM seam) → enqueue → tiered gate. If the chosen
    # workstream is registered, use its taste-integrated planning and fold in the
    # user's recalled preferences, so the agent builds *in the style learnt*.
    try:
        from xavani_learner.preferences import PreferenceStore

        preferences = PreferenceStore(state).recall()
    except Exception:
        preferences = []
    plan_ctx = {
        "tier_overrides": config.approval.tier_overrides,
        "config": config,
        "preferences": preferences,
    }
    workstream = get_workstream(intent.opportunity.workstream)
    if workstream is not None and hasattr(workstream, "make_plan"):
        proposal = workstream.make_plan(intent, ctx=plan_ctx, generate=generate)
    else:
        proposal = make_proposal(intent, ctx=plan_ctx, generate=generate)
    queue = ApprovalQueue(state, audit=AuditLog(state))
    queue.enqueue(proposal)
    status = gate(proposal, approver)
    if status != ProposalStatus.APPROVED:
        queue.set_status(proposal.id, status)
        report = CycleReport(
            cycle_id=cid, proposed=1,
            notes=f"proposal {proposal.id} {status.value} — awaiting your approval",
        )
        _finish(state, report, sender)
        return report
    queue.set_status(proposal.id, ProposalStatus.APPROVED)

    # Act → verify → (rollback on failure).
    results = execute_plan(
        proposal,
        handlers if handlers is not None else default_handlers(),
        ctx={"config": config, "state": state},
        reconfirm=reconfirm,
    )
    verdict = verify_step_results(results)
    if not verdict.ok and rollback is not None:
        rollback()

    # Report → learn.
    report = build_cycle_report(cid, proposal, results, verdict)
    queue.set_status(proposal.id, ProposalStatus.EXECUTED if verdict.ok else ProposalStatus.FAILED)
    record_outcome(state, report, intent.opportunity.kind, verdict.ok)
    _finish(state, report, sender)
    return report


def _finish(state, report: CycleReport, sender: Callable[[str], object] | None) -> None:
    """Checkpoint the cycle and deliver the report."""
    state.put("checkpoints", report.cycle_id, {
        "cycle_id": report.cycle_id,
        "notes": report.notes,
        "executed": report.executed,
        "verified": report.verified,
        "created_at": report.created_at,
    })
    if sender is not None:
        deliver_report(report, sender)


def last_checkpoint(state) -> dict | None:
    """The most recent cycle checkpoint, or ``None``."""
    cps = state.list("checkpoints")
    return max(cps, key=lambda c: c.get("created_at", 0)) if cps else None
