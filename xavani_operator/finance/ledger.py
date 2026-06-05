# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Finance ledger (v0.7.0 operator M-Biz finance).

Records income/expense entries (amounts in **integer cents**, VAT tracked
separately) in the operator state store and computes exact totals + the VAT
position (output − input = VAT due to SARS). Pure, deterministic (R10).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

_COLLECTION = "finance_ledger"


@dataclass
class LedgerEntry:
    """One income or expense line (amount is the VAT-inclusive total, in cents)."""

    id: str
    date: str            # ISO yyyy-mm-dd
    kind: str            # "income" | "expense"
    amount_cents: int
    vat_cents: int = 0
    category: str = "uncategorized"
    party: str = ""
    description: str = ""
    ref: str = ""
    paid: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "LedgerEntry":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class Ledger:
    """Persistent income/expense ledger with exact totals + VAT position."""

    def __init__(self, state: Any) -> None:
        self.state = state

    def add(self, entry: LedgerEntry) -> None:
        self.state.put(_COLLECTION, entry.id, entry.to_dict())

    def entries(self) -> list[LedgerEntry]:
        items = [LedgerEntry.from_dict(d) for d in self.state.list(_COLLECTION)]
        return sorted(items, key=lambda e: (e.date, e.id))

    def totals(self) -> dict[str, int]:
        income = expense = vat_output = vat_input = 0
        for e in self.entries():
            if e.kind == "income":
                income += e.amount_cents
                vat_output += e.vat_cents
            elif e.kind == "expense":
                expense += e.amount_cents
                vat_input += e.vat_cents
        return {
            "income": income,
            "expense": expense,
            "net": income - expense,
            "vat_output": vat_output,
            "vat_input": vat_input,
            "vat_due": vat_output - vat_input,
        }

    def by_category(self) -> dict[str, dict[str, int]]:
        out: dict[str, dict[str, int]] = {}
        for e in self.entries():
            bucket = out.setdefault(e.category, {"income": 0, "expense": 0})
            if e.kind in bucket:
                bucket[e.kind] += e.amount_cents
        return out
