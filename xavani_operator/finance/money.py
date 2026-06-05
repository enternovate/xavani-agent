# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Exact ZAR money + VAT math (v0.7.0 operator M-Biz finance).

Money is **integer cents** and all arithmetic goes through :class:`decimal.Decimal`
with ``ROUND_HALF_UP`` — never floats — so the finance core is exact and
auditable (a cent never goes missing). South-African defaults: ZAR, VAT 15%.
Pure, deterministic (R10).
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

_CENT = Decimal("1")


def rands_to_cents(value: str | int | float) -> int:
    """Parse ``"R1,234.56"`` / ``"100"`` / ``99.99`` → integer cents (>= 0)."""
    if isinstance(value, (int, float)):
        amount = Decimal(str(value))
    else:
        cleaned = str(value).strip().replace("R", "").replace(",", "").replace(" ", "")
        amount = Decimal(cleaned)
    if amount < 0:
        raise ValueError("amount cannot be negative")
    return int((amount * 100).quantize(_CENT, rounding=ROUND_HALF_UP))


def format_zar(cents: int) -> str:
    """Format integer cents as ``R1,234.56``."""
    rands = Decimal(cents) / 100
    return f"R{rands:,.2f}"


def vat_on_excl(excl_cents: int, rate: int | float = 15) -> int:
    """VAT amount (cents) on a VAT-exclusive amount, rounded half-up."""
    vat = (Decimal(excl_cents) * Decimal(str(rate)) / 100).quantize(_CENT, rounding=ROUND_HALF_UP)
    return int(vat)


def excl_to_incl(excl_cents: int, rate: int | float = 15) -> int:
    """VAT-inclusive total (cents) for a VAT-exclusive amount."""
    return excl_cents + vat_on_excl(excl_cents, rate)


def incl_to_excl(incl_cents: int, rate: int | float = 15) -> tuple[int, int]:
    """Split a VAT-inclusive amount into (exclusive, vat). They always sum to incl."""
    divisor = Decimal(1) + Decimal(str(rate)) / 100
    excl = int((Decimal(incl_cents) / divisor).quantize(_CENT, rounding=ROUND_HALF_UP))
    return excl, incl_cents - excl
