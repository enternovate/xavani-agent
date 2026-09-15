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

import hashlib
import json
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from xavani_operator.audit import action_event
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
        self._action_lock = threading.Lock()

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

    # -- R2 Task 19 / Code Pack O: exact, one-time action approvals ----------

    ACTION_COLLECTION = "action_approvals"

    def enqueue_action_for(self, request: "ActionRequest", *, approval_id: str) -> "BoundApproval":
        """Create and store a draft approval bound to ``request``'s identity."""
        return self.enqueue_action(BoundApproval.for_request(approval_id, request))

    def enqueue_action(self, approval: "BoundApproval") -> "BoundApproval":
        self._put_action(approval)
        self._action_audit("action-propose", approval)
        return approval

    def get_action(self, approval_id: str) -> "BoundApproval | None":
        d = self.state.get(self.ACTION_COLLECTION, approval_id)
        return BoundApproval.from_dict(d) if d else None

    def list_actions(self) -> list["BoundApproval"]:
        return [BoundApproval.from_dict(d) for d in self.state.list(self.ACTION_COLLECTION)]

    def request_approval(self, approval_id: str) -> "BoundApproval | None":
        approval = self.get_action(approval_id)
        if approval is None:
            return None
        transition_action(approval.state, "pending_approval")
        approval.state = "pending_approval"
        self._put_action(approval)
        self._action_audit("action-request", approval)
        return approval

    def approve_action(self, approval_id: str, *, now: float | None = None) -> "BoundApproval | None":
        approval = self.get_action(approval_id)
        if approval is None:
            return None
        transition_action(approval.state, "approved")
        approval.state = "approved"
        approval.expires_at = (time.time() if now is None else now) + APPROVAL_TTL_SECONDS
        self._put_action(approval)
        self._action_audit("action-approve", approval)
        return approval

    def deny_action(self, approval_id: str, *, now: float | None = None) -> "BoundApproval | None":
        approval = self.get_action(approval_id)
        if approval is None:
            return None
        transition_action(approval.state, "denied")
        approval.state = "denied"
        self._put_action(approval)
        self._action_audit("action-deny", approval)
        return approval

    def consume_action(
        self,
        approval_id: str,
        *,
        request: "ActionRequest | None" = None,
        now: float | None = None,
    ) -> tuple["BoundApproval | None", str]:
        """Atomically consume the single attempt an approval permits.

        Returns ``(record, reason)``; ``reason`` is empty on success. A
        consumed approval is never restored by a later failure. Only an
        approved, unexpired, digest-matching record may move to executing.
        """
        moment = time.time() if now is None else now
        with self._action_lock:
            approval = self.get_action(approval_id)
            if approval is None:
                return None, "unknown approval"
            if approval.consumed:
                return approval, "approval already consumed"
            if approval.state != "approved":
                return approval, f"approval is not executable (state: {approval.state})"
            if approval.expires_at is not None and moment > approval.expires_at:
                transition_action(approval.state, "expired")
                approval.state = "expired"
                self._put_action(approval)
                self._action_audit("action-expire", approval)
                return approval, "approval expired"
            if request is not None and request.digest() != approval.digest:
                return approval, "action context changed since approval"
            transition_action(approval.state, "executing")
            approval.state = "executing"
            approval.consumed = True
            approval.attempts += 1
            self._put_action(approval)
            self._action_audit("action-consume", approval)
            return approval, ""

    def resolve_action(self, approval_id: str, outcome: str, *, note: str = "") -> "BoundApproval | None":
        """Move executing/unknown to a terminal outcome (verified|failed|unknown)."""
        with self._action_lock:
            approval = self.get_action(approval_id)
            if approval is None:
                return None
            transition_action(approval.state, outcome)
            approval.state = outcome
            if note:
                approval.note = note
            self._put_action(approval)
            self._action_audit(f"action-{outcome}", approval)
            return approval

    def unresolved_unknown(self, request: "ActionRequest") -> "BoundApproval | None":
        """The unresolved unknown-outcome record guarding this exact action."""
        identity = request.to_dict()
        for approval in self.list_actions():
            if approval.state == "unknown" and approval.consumed and approval.request == identity:
                return approval
        return None

    def _put_action(self, approval: "BoundApproval") -> None:
        self.state.put(self.ACTION_COLLECTION, approval.id, approval.to_dict())

    def _action_audit(self, kind: str, approval: "BoundApproval") -> None:
        if self.audit is not None:
            self.audit.append(
                action_event(
                    kind,
                    approval_id=approval.id,
                    digest=approval.digest,
                    state=approval.state,
                    consumed=approval.consumed,
                ),
                min_level=1,
            )

    def _audit(self, kind: str, proposal_id: str, status: str) -> None:
        if self.audit is not None:
            self.audit.append({"type": kind, "proposal": proposal_id, "status": status})


# ---------------------------------------------------------------------------
# R2 Task 19 / Code Pack O: exact action identity
# ---------------------------------------------------------------------------

APPROVAL_TTL_SECONDS = 300

ACTION_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "draft": ("pending_approval",),
    "pending_approval": ("approved", "denied", "expired"),
    "approved": ("executing", "expired"),
    "executing": ("verified", "failed", "unknown"),
    "unknown": ("verified", "failed"),
}
# Note: approved -> expired is a bookkeeping move only (an approval whose
# 5-minute window passed before use). Expired never executes.


def transition_action(current: str, target: str) -> str:
    """Validate one step of the action state machine; return ``target``.

    No other transition may execute an external action, and an ``unknown``
    action can never go back to ``executing``.
    """
    if target not in ACTION_TRANSITIONS.get(current, ()):
        raise ValueError(f"Invalid action transition: {current} -> {target}")
    return target


def action_can_execute(state: str) -> bool:
    """Only an approved action may start executing."""
    return state == "approved"


def action_digest(*, profile: str, workspace_id: str, operation: str, target: str, payload: dict) -> str:
    """The canonical digest of an exact action identity (Code Pack O)."""
    if not all(isinstance(value, str) and value for value in (profile, workspace_id, operation, target)):
        raise ValueError("The action identity is incomplete.")
    raw = json.dumps(
        {
            "profile": profile,
            "workspace_id": workspace_id,
            "operation": operation,
            "target": target,
            "payload": payload,
        },
        sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@dataclass
class ActionRequest:
    """The exact action identity an approval is bound to."""

    profile: str
    workspace_id: str
    operation: str
    target: str
    payload: dict[str, Any] = field(default_factory=dict)

    def digest(self) -> str:
        return action_digest(
            profile=self.profile,
            workspace_id=self.workspace_id,
            operation=self.operation,
            target=self.target,
            payload=self.payload,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile,
            "workspace_id": self.workspace_id,
            "operation": self.operation,
            "target": self.target,
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ActionRequest":
        return cls(
            profile=d["profile"],
            workspace_id=d["workspace_id"],
            operation=d["operation"],
            target=d["target"],
            payload=dict(d.get("payload") or {}),
        )


@dataclass
class BoundApproval:
    """A one-time approval storing the digest, expiry, and consumed state."""

    id: str
    request: dict[str, Any]
    digest: str
    state: str = "draft"
    consumed: bool = False
    attempts: int = 0
    created_at: float = 0.0
    expires_at: float | None = None
    note: str = ""

    @classmethod
    def for_request(cls, approval_id: str, request: ActionRequest, *, created_at: float | None = None) -> "BoundApproval":
        return cls(
            id=approval_id,
            request=request.to_dict(),
            digest=request.digest(),
            created_at=time.time() if created_at is None else created_at,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "request": self.request,
            "digest": self.digest,
            "state": self.state,
            "consumed": self.consumed,
            "attempts": self.attempts,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "BoundApproval":
        return cls(
            id=d["id"],
            request=dict(d.get("request") or {}),
            digest=d.get("digest", ""),
            state=d.get("state", "draft"),
            consumed=bool(d.get("consumed")),
            attempts=int(d.get("attempts") or 0),
            created_at=float(d.get("created_at") or 0.0),
            expires_at=d.get("expires_at"),
            note=d.get("note", ""),
        )
