# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for exact ZAR / VAT money math (v0.7.0 operator M-Biz finance)."""

from __future__ import annotations

import pytest

from xavani_operator.finance.money import (
    excl_to_incl,
    format_zar,
    incl_to_excl,
    rands_to_cents,
    vat_on_excl,
)


def test_rands_to_cents_parses_formats():
    assert rands_to_cents("R1,234.56") == 123456
    assert rands_to_cents("100") == 10000
    assert rands_to_cents("99.99") == 9999
    assert rands_to_cents(50) == 5000
    assert rands_to_cents(0) == 0


def test_format_zar():
    assert format_zar(123456) == "R1,234.56"
    assert format_zar(10000) == "R100.00"
    assert format_zar(5) == "R0.05"


def test_vat_on_exclusive_amount():
    assert vat_on_excl(10000, 15) == 1500   # R100 excl -> R15 VAT
    assert vat_on_excl(0, 15) == 0


def test_vat_rounds_half_up():
    # R33.33 excl * 15% = R4.9995 -> rounds to R5.00
    assert vat_on_excl(3333, 15) == 500


def test_excl_to_incl_and_back():
    assert excl_to_incl(10000, 15) == 11500
    excl, vat = incl_to_excl(11500, 15)
    assert excl == 10000
    assert vat == 1500


def test_incl_to_excl_reconciles_to_total():
    # Whatever the rounding, excl + vat must equal the inclusive total.
    for incl in (10000, 12345, 99999, 1):
        excl, vat = incl_to_excl(incl, 15)
        assert excl + vat == incl


def test_negative_amount_rejected():
    with pytest.raises(ValueError):
        rands_to_cents("-5")
