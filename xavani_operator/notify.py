# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Approval delivery / notification (v0.7.0 operator U30).

When a proposal needs the user, the operator can reach them on their own channel
(Telegram, Discord, email, …) rather than waiting for them to check a CLI. This
module renders a human-readable approval request and delivers it via an
**injected** ``sender`` callable — the loop wires a real one over
``tools/send_message_tool`` in M3, while tests pass a list's ``append``.

Rendering is deterministic and import-light (no LLM, no client) — the model and
the network live behind the injected sender, never here.
"""

from __future__ import annotations

from typing import Callable

from xavani_operator.types import Proposal


def format_approval_request(proposal: Proposal, config) -> str:
    """Render a concise, human-readable approval request for ``proposal``."""
    opp = proposal.intent.opportunity
    lines = [
        f"🔔 Xavani needs your approval — {config.product.name}",
        f"Proposal {proposal.id}: {opp.workstream}/{opp.kind}",
        f"  {opp.rationale}".rstrip(),
        "Plan:",
    ]
    for step in proposal.steps:
        lines.append(f"  [{step.tier.name}] {step.action_class} — {step.summary}")
    lines.append(f"Approve:  xavani operator approve {proposal.id}")
    lines.append(f"Reject:   xavani operator reject {proposal.id}")
    return "\n".join(lines)


def deliver_approval_request(
    proposal: Proposal,
    config,
    sender: Callable[[str], object] | None = None,
) -> bool:
    """Deliver the approval request via ``sender``; return whether it was sent."""
    message = format_approval_request(proposal, config)
    if sender is None:
        return False
    sender(message)
    return True
