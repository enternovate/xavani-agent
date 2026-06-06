# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""CLI for the finance core — `xavani finance` (v0.7.0 operator M-Biz finance).

Connects the finance subsystem into one usable command: record income/expenses
(auto-categorised + VAT), show the ledger, run an audit (VAT due, anomalies),
and generate a payment INSTRUCTION (EFT or SA payment-link). The agent instructs;
you execute. Import-light; heavy logic lives in the finance modules.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any


def cmd_finance(args: Any) -> None:
    """Dispatch a ``xavani finance <subcommand>`` invocation."""
    command = getattr(args, "finance_command", None)
    handler = {
        "add": _cmd_add,
        "ledger": _cmd_ledger,
        "audit": _cmd_audit,
        "pay": _cmd_pay,
    }.get(command)
    if handler is None:
        _usage()
    else:
        handler(args)


def _state():
    from xavani_operator.state import OperatorState

    return OperatorState()


def _cmd_add(args: Any) -> None:
    from xavani_operator.finance.categories import categorize, is_vat_claimable
    from xavani_operator.finance.ledger import Ledger, LedgerEntry
    from xavani_operator.finance.money import format_zar, rands_to_cents, vat_on_excl

    kind = getattr(args, "kind", "expense")
    if kind not in ("income", "expense"):
        print("Usage: xavani finance add <income|expense> <amount> [--category ...]")
        return
    try:
        excl = rands_to_cents(getattr(args, "amount", "0"))
    except Exception as exc:
        print(f"✗ bad amount: {exc}")
        return
    desc = getattr(args, "desc", "") or ""
    category = getattr(args, "category", None) or categorize(desc, kind)
    vat = vat_on_excl(excl) if (kind == "income" or is_vat_claimable(category)) else 0
    entry = LedgerEntry(
        id=f"e-{uuid.uuid4().hex[:10]}",
        date=getattr(args, "date", None) or datetime.date.today().isoformat(),
        kind=kind,
        amount_cents=excl + vat,
        vat_cents=vat,
        category=category,
        party=getattr(args, "party", "") or "",
        description=desc,
        ref=getattr(args, "ref", "") or "",
        paid=not bool(getattr(args, "unpaid", False)),
    )
    Ledger(_state()).add(entry)
    print(f"✓ Added {kind} {format_zar(entry.amount_cents)} [{category}] (VAT {format_zar(vat)}) — id {entry.id}")


def _cmd_ledger(args: Any) -> None:
    from xavani_operator.finance.ledger import Ledger
    from xavani_operator.finance.money import format_zar

    led = Ledger(_state())
    entries = led.entries()
    if not entries:
        print("Ledger is empty. Add with `xavani finance add income|expense <amount>`.")
        return
    for e in entries:
        flag = "" if e.paid else " (UNPAID)"
        print(f"  {e.date}  {e.kind:<7} {format_zar(e.amount_cents):>12}  [{e.category}] {e.party}{flag}")
    t = led.totals()
    print(
        f"— income {format_zar(t['income'])} · expense {format_zar(t['expense'])} · "
        f"net {format_zar(t['net'])} · VAT due {format_zar(t['vat_due'])}"
    )


def _cmd_audit(args: Any) -> None:
    from xavani_operator.finance.audit import audit, render_audit
    from xavani_operator.finance.ledger import Ledger

    print(render_audit(audit(Ledger(_state()))))


def _cmd_pay(args: Any) -> None:
    from xavani_operator.finance.money import rands_to_cents
    from xavani_operator.finance.payments import (
        eft_instruction,
        payment_link_instruction,
        render_instruction,
    )

    method = getattr(args, "method", "eft")
    try:
        amount_cents = rands_to_cents(getattr(args, "amount", "0"))
    except Exception as exc:
        print(f"✗ bad amount: {exc}")
        return
    ref = getattr(args, "ref", "") or ""
    if method == "link":
        try:
            instr = payment_link_instruction(getattr(args, "rail", "") or "", amount_cents, ref)
        except ValueError as exc:
            print(f"✗ {exc}")
            return
    else:
        instr = eft_instruction(
            getattr(args, "to", "") or "", getattr(args, "account", "") or "",
            getattr(args, "branch", "") or "", amount_cents, ref,
        )
    print("📋 Payment instruction (Tier-2 — you approve & execute):")
    print("  " + render_instruction(instr))


def _usage() -> None:
    print("xavani finance — track money + audit (ZAR/VAT, SARS); the agent instructs, you pay")
    print("  add <income|expense> <amount> [--category --party --ref --desc --date --unpaid]")
    print("  ledger                 show entries + totals + VAT due")
    print("  audit                  reconcile: VAT due, uncategorized, unpaid, anomalies")
    print("  pay --method eft  --to <name> --account <no> --branch <code> --amount <R> --ref <r>")
    print("  pay --method link --rail <payfast|yoco|ozow|snapscan> --amount <R> --ref <r>")
