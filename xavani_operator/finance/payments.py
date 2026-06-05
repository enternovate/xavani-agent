# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Payment-instruction generation — SA rails (v0.7.0 operator M-Biz finance).

The agent **instructs**, the user **executes**. These functions produce a
structured payment *instruction* (EFT, or a PayFast/Yoco/Ozow/SnapScan request)
that the user actions — the agent never moves money or touches real banking
details. Generation is deterministic (R10); posting it is a Tier-2 approval-gated,
audit-logged action upstream.
"""

from __future__ import annotations

from xavani_operator.finance.money import format_zar

_RAILS = {"payfast", "yoco", "ozow", "snapscan"}


def eft_instruction(
    beneficiary: str,
    account: str,
    branch_code: str,
    amount_cents: int,
    reference: str,
    bank: str = "",
) -> dict:
    """A manual EFT payment instruction for the user to pay via their bank."""
    return {
        "method": "eft",
        "beneficiary": beneficiary,
        "bank": bank,
        "account": account,
        "branch_code": branch_code,
        "amount_cents": amount_cents,
        "amount": format_zar(amount_cents),
        "reference": reference,
        "action": "You pay this manually via your bank / EFT app — Xavani never moves money.",
    }


def payment_link_instruction(rail: str, amount_cents: int, reference: str, recipient: str = "") -> dict:
    """A request to collect/pay via an SA payment-link rail (you create the link)."""
    rail = rail.lower()
    if rail not in _RAILS:
        raise ValueError(f"unsupported payment rail: {rail!r} (expected one of {sorted(_RAILS)})")
    return {
        "method": "payment_link",
        "rail": rail,
        "amount_cents": amount_cents,
        "amount": format_zar(amount_cents),
        "reference": reference,
        "recipient": recipient,
        "action": f"Create a {rail} payment request/link for this amount and send it — you generate and approve the link.",
    }


def render_instruction(instr: dict) -> str:
    """Human-readable one-liner for a payment instruction."""
    base = f"Pay {instr['amount']} (ref {instr.get('reference', '')})"
    if instr.get("method") == "eft":
        return (
            f"{base} via EFT to {instr['beneficiary']} "
            f"acc {instr['account']} branch {instr['branch_code']}. {instr['action']}"
        )
    return f"{base} via {instr.get('rail', 'link')}. {instr['action']}"
