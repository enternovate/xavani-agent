# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Xavani Operator — the autonomy layer (v0.7.0 → v0.9.0).

A self-initiating, approval-gated control loop that turns Xavani into a full
**operator**: it perceives a plugged-in product (a repo + ``xavani.product.yaml``),
decides what is most worth doing, proposes a concrete plan, waits for the user to
approve, then acts (build *and* promote), verifies, reports, and learns.

Design spine (R10): every *decision* — perceive, opportunity detection, ranking,
tier classification, verify-gating — is pure Python and makes **zero** model
calls. The LLM is used only to *generate* (plans, code, copy). See
``planning/v0.7.0/DESIGN.md``.

This package builds on existing primitives rather than reinventing them
(``tools/approval.py``, ``delegate_tool``, ``cronjob_tools``, ``checkpoint_manager``,
``xavani_memory``, ``gateway/platforms/*``).
"""

from __future__ import annotations

from xavani_operator.types import (
    CycleReport,
    Intent,
    Opportunity,
    Perception,
    PlanStep,
    Proposal,
    ProposalStatus,
    StepResult,
    Tier,
    Verdict,
)

__all__ = [
    "CycleReport",
    "Intent",
    "Opportunity",
    "Perception",
    "PlanStep",
    "Proposal",
    "ProposalStatus",
    "StepResult",
    "Tier",
    "Verdict",
]
