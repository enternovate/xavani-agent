# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Core data types for the Xavani Operator autonomy layer (v0.7.0 operator U1).

These are plain, dependency-light dataclasses and enums shared across the
operator's control loop (perceive → opportunities → decide → propose → approve →
act → verify → report → learn). They carry **no behaviour that needs an LLM**
(R10): a ``Verdict`` is a verdict, a ``Tier`` is a tier, an ``Opportunity`` is a
scored candidate. Keeping these inert and import-light means every deterministic
module in the package can depend on them without pulling in a model client.
"""

from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field
from typing import Any


class Tier(enum.IntEnum):
    """Approval tier for an action. Higher = more restrictive (needs more consent).

    * ``AUTO`` (0)   — safe, reversible, local. Runs silently, logged.
    * ``NOTIFY`` (1) — low-risk; runs but pings the user (veto window).
    * ``APPROVE`` (2)— risky/costly/outward-facing; blocks for explicit approval.
    * ``BLOCK`` (3)  — destructive/irreversible; per-action confirmation, always.
    """

    AUTO = 0
    NOTIFY = 1
    APPROVE = 2
    BLOCK = 3


class ProposalStatus(enum.Enum):
    """Lifecycle status of a proposal in the approval queue."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    AMENDED = "amended"
    EXPIRED = "expired"
    EXECUTED = "executed"
    FAILED = "failed"


@dataclass
class Verdict:
    """The deterministic result of a check (gate, verify, policy)."""

    ok: bool
    findings: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @classmethod
    def ok_(cls, *, warnings: list[str] | None = None) -> "Verdict":
        """A passing verdict (optionally with non-blocking warnings)."""
        return cls(ok=True, findings=[], warnings=list(warnings or []))

    @classmethod
    def fail(cls, reason: str, *, warnings: list[str] | None = None) -> "Verdict":
        """A failing verdict carrying the blocking reason as a finding."""
        return cls(ok=False, findings=[reason], warnings=list(warnings or []))


@dataclass
class Opportunity:
    """A scored candidate action surfaced deterministically from a Perception.

    ``score`` is a pure-Python relevance/priority score in roughly [0, 1]; the
    decision step ranks Opportunities by it (descending). ``workstream`` names the
    pack that produced it ("build" / "promote" / "ops").
    """

    id: str
    kind: str
    workstream: str
    score: float
    rationale: str = ""
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class Intent:
    """The chosen Opportunity plus any decision-time parameters."""

    opportunity: Opportunity
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanStep:
    """One step of a proposed plan, tagged with the approval tier it requires."""

    id: str
    action_class: str
    tier: Tier
    summary: str = ""
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class Proposal:
    """A concrete plan awaiting (or having passed) human approval."""

    id: str
    intent: Intent
    steps: list[PlanStep] = field(default_factory=list)
    status: ProposalStatus = ProposalStatus.PENDING
    created_at: float = field(default_factory=time.time)
    notes: str = ""


@dataclass
class StepResult:
    """The outcome of executing a single PlanStep."""

    step_id: str
    ok: bool
    output: str = ""
    error: str = ""


@dataclass
class CycleReport:
    """A summary of one operator cycle, for the user and for `learn`."""

    cycle_id: str
    proposed: int = 0
    approved: int = 0
    executed: int = 0
    verified: int = 0
    learned: int = 0
    notes: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass
class Perception:
    """A deterministic snapshot of a product's state at one moment.

    Assembled by :func:`xavani_operator.perceive.perceive` from read-only
    collectors. ``content_hash`` is a stable digest of the signal sections so the
    loop can cheaply detect "nothing changed" and skip a cycle.
    """

    repo: dict[str, Any] = field(default_factory=dict)
    tests: dict[str, Any] = field(default_factory=dict)
    issues: list[dict[str, Any]] = field(default_factory=list)
    channels: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    last_cycle: dict[str, Any] | None = None
    content_hash: str = ""
    created_at: float = field(default_factory=time.time)
