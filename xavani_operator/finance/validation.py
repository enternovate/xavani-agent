# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Deterministic finance validation (R3 reliability, Task 18).

Pure, no I/O, no clock: the same input always produces the same verdict or the
same exception. Every check rejects rather than repairs, so invalid source data
cannot reach a verified financial report.

This module validates a narrow statement/row schema. It is not a workbook
validator and it does not validate ISO currency codes, dates, or schema
versions -- a source adapter shall do that before calling these functions.
Money is integer minor units or decimal strings; floats are rejected so a
binary rounding error can never enter the ledger.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

_MINOR_UNIT = Decimal("1")
_CONVERSION_SEPARATOR = ">"


class FinanceValidationError(ValueError):
    """A financial input is missing, ill-typed, or internally inconsistent."""


def finite_decimal(value) -> Decimal:
    """Coerce a decimal string / int / Decimal to a finite Decimal.

    Rejects floats (binary rounding), booleans (they are ints in Python), and
    non-finite decimals (NaN, Infinity, -Infinity).
    """
    if isinstance(value, (float, bool)) or not isinstance(value, (str, int, Decimal)):
        raise FinanceValidationError("Use a decimal string or an integer.")
    try:
        number = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise FinanceValidationError("The financial value is invalid.") from exc
    if not number.is_finite():
        raise FinanceValidationError("The financial value shall be finite.")
    return number


def money_minor_units(value) -> int:
    """Money as integer minor units, or an integral decimal string.

    Negative values are retained: the schema permits them (credits, refunds,
    negative equity). A float or a fractional minor unit is rejected.
    """
    if isinstance(value, (bool, float)):
        raise FinanceValidationError("Money shall be integer minor units, not a float.")
    if isinstance(value, int):
        return value
    amount = finite_decimal(value)
    if amount != amount.to_integral_value():
        raise FinanceValidationError("Money in minor units shall be a whole number.")
    return int(amount)


def _required_text(source: dict, field: str, subject: str = "statement") -> str:
    value = source.get(field)
    if not isinstance(value, str) or not value.strip():
        raise FinanceValidationError(f"The {subject} requires {field}.")
    return value


def validate_statement(statement: dict) -> dict:
    """Require currency, period, and source, then require assets - liabilities - equity == 0."""
    if not isinstance(statement, dict):
        raise FinanceValidationError("The statement shall contain an object.")
    for field in ("currency", "period", "source"):
        _required_text(statement, field)
    assets = finite_decimal(statement.get("assets"))
    liabilities = finite_decimal(statement.get("liabilities"))
    equity = finite_decimal(statement.get("equity"))
    difference = assets - liabilities - equity
    if difference != 0:
        raise FinanceValidationError(f"The statement does not balance: {difference}.")
    return {"currency": statement["currency"], "period": statement["period"], "difference": "0"}


def safe_ratio(numerator, denominator) -> str | None:
    """A ratio, or None when the denominator is zero (unavailable, never 0)."""
    top = finite_decimal(numerator)
    bottom = finite_decimal(denominator)
    return None if bottom == 0 else str(top / bottom)


def validate_dcf_rates(discount_rate, terminal_growth) -> tuple[Decimal, Decimal]:
    """A perpetual-growth DCF requires discount_rate > terminal_growth."""
    discount = finite_decimal(discount_rate)
    growth = finite_decimal(terminal_growth)
    if discount <= growth:
        raise FinanceValidationError("The discount rate shall exceed terminal growth.")
    return discount, growth


def duplicate_invoices(rows: list[dict]) -> tuple[str, ...]:
    """Invoice numbers whose (supplier_id, invoice_number, currency) identity repeats."""
    seen = set()
    duplicates = []
    for row in rows:
        key = tuple(row.get(field) for field in ("supplier_id", "invoice_number", "currency"))
        if not all(isinstance(value, str) and value.strip() for value in key):
            raise FinanceValidationError("An invoice identity is incomplete.")
        if key in seen:
            duplicates.append(row["invoice_number"])
        seen.add(key)
    return tuple(duplicates)


def _conversion_rate(conversions, source_currency: str, target_currency: str) -> Decimal:
    if not isinstance(conversions, dict):
        raise FinanceValidationError("Mixed currencies require explicit conversion data.")
    key = f"{source_currency}{_CONVERSION_SEPARATOR}{target_currency}"
    raw = conversions.get(key)
    if raw is None:
        raise FinanceValidationError(f"Missing conversion data for {key}.")
    rate = finite_decimal(raw)
    if rate <= 0:
        raise FinanceValidationError(f"The conversion rate for {key} shall be positive.")
    return rate


def single_currency(rows: list[dict], *, reporting_currency=None, conversions=None) -> str:
    """The single currency of a row set, or the reporting currency once converted.

    Mixed currencies are rejected unless explicit conversion data covers every
    currency present.
    """
    if not isinstance(rows, list) or not rows:
        raise FinanceValidationError("The statement requires at least one row.")
    currencies: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            raise FinanceValidationError("A row shall contain an object.")
        code = _required_text(row, "currency", subject="row")
        if code not in currencies:
            currencies.append(code)
    if len(currencies) == 1:
        return currencies[0]
    if not isinstance(reporting_currency, str) or not reporting_currency.strip():
        raise FinanceValidationError("Mixed currencies require a reporting currency.")
    for code in currencies:
        if code != reporting_currency:
            _conversion_rate(conversions, code, reporting_currency)
    return reporting_currency


def convert_minor_units(amount_minor, *, source_currency: str, target_currency: str, conversions) -> int:
    """Convert integer minor units with an explicit rate, rounding half-up."""
    amount = money_minor_units(amount_minor)
    if source_currency == target_currency:
        return amount
    rate = _conversion_rate(conversions, source_currency, target_currency)
    return int((Decimal(amount) * rate).quantize(_MINOR_UNIT, rounding=ROUND_HALF_UP))


def validate_tax_rate(rate, jurisdiction) -> tuple[Decimal, str]:
    """A tax calculation requires an explicit rate and a jurisdiction."""
    if rate is None or not isinstance(rate, (str, int, Decimal)) or isinstance(rate, bool):
        raise FinanceValidationError("A tax calculation requires an explicit rate.")
    value = finite_decimal(rate)
    if not 0 <= value <= 1:
        raise FinanceValidationError("The tax rate shall be a fraction between 0 and 1.")
    return value, _required_text({"jurisdiction": jurisdiction}, "jurisdiction", subject="tax")


def tax_on_minor_units(amount_minor, *, rate, jurisdiction) -> int:
    """Tax in minor units on an amount, rounded half-up; requires rate + jurisdiction."""
    base = money_minor_units(amount_minor)
    fraction, _ = validate_tax_rate(rate, jurisdiction)
    return int((Decimal(base) * fraction).quantize(_MINOR_UNIT, rounding=ROUND_HALF_UP))
