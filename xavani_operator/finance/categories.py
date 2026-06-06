# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""SARS-aligned expense/income categorizer (v0.7.0 operator M-Biz finance).

Deterministic keyword rules map a transaction description to a tax-aligned
category (rent, salaries, marketing, cost of sales, …) so the ledger and audit
can produce a SARS-shaped picture. Pure Python, no LLM (R10); this is
classification, not money math.
"""

from __future__ import annotations

import re

# Ordered: more specific categories first; generic ("office") last.
_RULES: list[tuple[tuple[str, ...], str]] = [
    (("rent", "lease"), "rent"),
    (("salar", "wage", "payroll"), "salaries"),
    (("market", "advert", "campaign", "facebook", "instagram", "google ad", "ad spend"), "marketing"),
    (("fuel", "petrol", "travel", "uber", "flight", "mileage"), "travel"),
    (("stock", "inventory", "supplier", "cost of good", "raw material"), "cost_of_sales"),
    (("software", "subscription", "saas", "hosting", "domain", "licen", "xero"), "software"),
    (("legal", "accounting", "consult", "professional", "audit fee"), "professional_fees"),
    (("bank charge", "transaction fee", "card fee"), "bank_charges"),
    (("electricity", "water", "utilit", "internet", "airtime", "telephone"), "utilities"),
    (("insurance",), "insurance"),
    (("repair", "maintenance"), "maintenance"),
    (("office", "stationery", "supplies"), "office"),
]

# Categories that carry no input VAT (cannot be claimed).
_VAT_EXEMPT = {"salaries", "interest", "interest_income"}


def categorize(description: str, kind: str = "expense") -> str:
    """Map a description to a SARS-aligned category (``uncategorized`` if unknown)."""
    low = (description or "").lower()
    for keywords, category in _RULES:
        for kw in keywords:
            if re.search(r"\b" + re.escape(kw), low):
                return category
    return "uncategorized"


def is_vat_claimable(category: str) -> bool:
    """True if input VAT on this category can be claimed (deterministic rule)."""
    return category not in _VAT_EXEMPT
