# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Finance audit / reconcile report (v0.7.0 operator M-Biz finance).

A deterministic (R10) audit over the ledger: exact totals + VAT position
(output − input = VAT due to SARS), plus flags a real audit would want —
uncategorized entries, unpaid (outstanding) entries, duplicate references, and
negative amounts. No LLM, no guesswork; just the books, reconciled.
"""

from __future__ import annotations

from typing import Any

from xavani_operator.finance.money import format_zar


def audit(ledger: Any) -> dict:
    """Reconcile the ledger into an audit report dict (all amounts in cents)."""
    entries = ledger.entries()
    totals = ledger.totals()

    uncategorized = sum(1 for e in entries if e.category == "uncategorized")
    unpaid = sum(1 for e in entries if not e.paid)
    negatives = sum(1 for e in entries if e.amount_cents < 0)

    ref_counts: dict[str, int] = {}
    for e in entries:
        if e.ref:
            ref_counts[e.ref] = ref_counts.get(e.ref, 0) + 1
    duplicate_refs = sorted(r for r, c in ref_counts.items() if c > 1)

    return {
        **totals,
        "entries": len(entries),
        "uncategorized": uncategorized,
        "unpaid": unpaid,
        "negatives": negatives,
        "duplicate_refs": duplicate_refs,
        "anomalies": negatives + len(duplicate_refs),
    }


def render_audit(report: dict) -> str:
    """Render an audit report as a short, human-readable block (ZAR)."""
    return "\n".join([
        "Finance audit (ZAR)",
        f"  income {format_zar(report['income'])} · expense {format_zar(report['expense'])} · "
        f"net {format_zar(report['net'])}",
        f"  VAT output {format_zar(report['vat_output'])} − input {format_zar(report['vat_input'])} "
        f"= due {format_zar(report['vat_due'])}",
        f"  entries {report['entries']} · uncategorized {report['uncategorized']} · "
        f"unpaid {report['unpaid']} · anomalies {report['anomalies']}",
    ])
