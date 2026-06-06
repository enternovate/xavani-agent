# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the SARS-aligned categorizer (v0.7.0 operator M-Biz finance)."""

from __future__ import annotations

from xavani_operator.finance.categories import categorize, is_vat_claimable


def test_categorize_common_expenses():
    assert categorize("Office rent for June") == "rent"
    assert categorize("Facebook ad campaign spend") == "marketing"
    assert categorize("Salary - John Dlamini") == "salaries"
    assert categorize("Petrol / fuel for deliveries") == "travel"
    assert categorize("Stock from supplier") == "cost_of_sales"
    assert categorize("Xero software subscription") == "software"


def test_unrecognised_is_uncategorized():
    assert categorize("a totally random thing") == "uncategorized"


def test_vat_claimable_rules():
    assert is_vat_claimable("marketing") is True
    assert is_vat_claimable("rent") is True
    assert is_vat_claimable("salaries") is False     # salaries carry no VAT
    assert is_vat_claimable("interest") is False
