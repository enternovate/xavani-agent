# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Approval queue + tiered gate (v0.7.0 operator U25–U27/U32).

The "you just approve" half of the operator. Proposals are persisted here and
move through statuses (pending → approved/rejected). The **tiered gate** decides
whether a plan can run on its own or needs a human:

* a plan with only Tier 0/1 steps **auto-approves** (nothing outward/risky);
* a plan with any Tier ≥ APPROVE step **blocks** for a human decision;
* approving a plan authorizes its Tier ≤ APPROVE steps, but **Tier 3 (BLOCK)
  steps still re-confirm at execution** (handled by ``act`` in M3).

All of this is deterministic (R10). Every state change can be written to a
hash-chained :class:`~xavani_operator.audit.AuditLog` for accountability.
"""

from __future__ import annotations

import time
from typing import Callable

from xavani_operator.propose import proposal_from_dict, proposal_to_dict
from xavani_operator.types import PlanStep, Proposal, ProposalStatus, Tier


def needs_approval(proposal: Proposal) -> bool:
    """True if any step needs explicit human consent (Tier ≥ APPROVE)."""
    return any(s.tier >= Tier.APPROVE for s in proposal.steps)


def authorized_steps(proposal: Proposal) -> list[PlanStep]:
    """Steps a plan-level approval authorizes to run (Tier ≤ APPROVE)."""
    return [s for s in proposal.steps if s.tier <= Tier.APPROVE]


def reconfirm_steps(proposal: Proposal) -> list[PlanStep]:
    """Steps that always require per-action re-confirmation (Tier == BLOCK)."""
    return [s for s in proposal.steps if s.tier == Tier.BLOCK]


def gate(proposal: Proposal, approver: Callable[[Proposal], bool] | None = None) -> ProposalStatus:
    """Decide a proposal's status under tiered approval.

    * No Tier ≥ APPROVE steps → :attr:`ProposalStatus.APPROVED` (auto).
    * Otherwise → ``approver(proposal)`` decides; with no approver the proposal
      stays :attr:`ProposalStatus.PENDING` (awaiting a human).
    """
    if not needs_approval(proposal):
        return ProposalStatus.APPROVED
    if approver is None:
        return ProposalStatus.PENDING
    return ProposalStatus.APPROVED if approver(proposal) else ProposalStatus.REJECTED


def veto_window_elapsed(created_at: float, auto_window: int, now: float | None = None) -> bool:
    """True once a Tier-1 step may auto-proceed (its veto window has passed)."""
    if auto_window <= 0:
        return True
    now = time.time() if now is None else now
    return (now - created_at) >= auto_window


class ApprovalQueue:
    """Persistent queue of proposals awaiting (or having passed) approval."""

    COLLECTION = "proposals"

    def __init__(self, state, audit=None) -> None:
        self.state = state
        self.audit = audit

    def enqueue(self, proposal: Proposal) -> None:
        self.state.put(self.COLLECTION, proposal.id, proposal_to_dict(proposal))
        self._audit("enqueue", proposal.id, proposal.status.value)

    def get(self, proposal_id: str) -> Proposal | None:
        d = self.state.get(self.COLLECTION, proposal_id)
        return proposal_from_dict(d) if d else None

    def list(self, status: ProposalStatus | None = None) -> list[Proposal]:
        proposals = [proposal_from_dict(d) for d in self.state.list(self.COLLECTION)]
        if status is not None:
            proposals = [p for p in proposals if p.status == status]
        return proposals

    def set_status(self, proposal_id: str, status: ProposalStatus) -> Proposal | None:
        d = self.state.get(self.COLLECTION, proposal_id)
        if d is None:
            return None
        d["status"] = status.value
        self.state.put(self.COLLECTION, proposal_id, d)
        self._audit("status", proposal_id, status.value)
        return proposal_from_dict(d)

    def approve(self, proposal_id: str) -> Proposal | None:
        return self.set_status(proposal_id, ProposalStatus.APPROVED)

    def reject(self, proposal_id: str) -> Proposal | None:
        return self.set_status(proposal_id, ProposalStatus.REJECTED)

    def _audit(self, kind: str, proposal_id: str, status: str) -> None:
        if self.audit is not None:
            self.audit.append({"type": kind, "proposal": proposal_id, "status": status})
