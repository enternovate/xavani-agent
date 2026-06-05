# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Deterministic approval-tier classifier (v0.7.0 operator U4).

Maps an *action class* (the kind of thing a plan step does, e.g. ``run_tests`` or
``post_external``) to the :class:`~xavani_operator.types.Tier` of consent it
needs. This is the heart of the "it initiates, I just approve" UX: the operator
proposes a plan, every step is classified here, and the approval gate uses the
tier to decide what runs silently vs. what blocks for the user.

Pure Python, **no LLM and no I/O** (R10) — tier is a property of the action, not
something to ask a model about. Unknown action classes fail *safe*: they default
to ``APPROVE`` so a human sees anything we don't explicitly recognise.
"""

from __future__ import annotations

from xavani_operator.types import Tier

# Default action-class → tier mapping. Conservative by construction.
DEFAULT_TIERS: dict[str, Tier] = {
    # Tier 0 — Auto: safe, reversible, local.
    "read": Tier.AUTO,
    "analyze": Tier.AUTO,
    "run_tests": Tier.AUTO,
    "lint": Tier.AUTO,
    "draft_staging": Tier.AUTO,
    "commit_workbranch": Tier.AUTO,
    # Tier 1 — Notify: low-risk, worth a heads-up.
    "open_draft_pr": Tier.NOTIFY,
    "create_issue": Tier.NOTIFY,
    "stage_content": Tier.NOTIFY,
    # Tier 2 — Approve: risky / costly / outward-facing.
    "merge": Tier.APPROVE,
    "deploy": Tier.APPROVE,
    "publish": Tier.APPROVE,
    "post_external": Tier.APPROVE,
    "send_external": Tier.APPROVE,
    "spend": Tier.APPROVE,
    "delete": Tier.APPROVE,
    # Tier 3 — Block: destructive / irreversible.
    "force_push": Tier.BLOCK,
    "prod_data_op": Tier.BLOCK,
    "payment": Tier.BLOCK,
}

# Unknown action classes need a human by default (fail safe).
UNKNOWN_TIER: Tier = Tier.APPROVE


def classify(
    action_class: str,
    overrides: dict[str, int | Tier] | None = None,
) -> Tier:
    """Return the :class:`Tier` required for ``action_class``.

    ``overrides`` (typically from ``approval.tier_overrides`` in the product
    config) wins over the defaults and may raise *or* lower a tier. Override
    values may be a :class:`Tier` or a plain ``int`` (0–3).
    """
    if overrides and action_class in overrides:
        return Tier(int(overrides[action_class]))
    return DEFAULT_TIERS.get(action_class, UNKNOWN_TIER)
