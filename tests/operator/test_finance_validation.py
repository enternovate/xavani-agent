# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for deterministic finance validation (R3 reliability, Task 18).

Cases load from ``tests/fixtures/business/finance_cases.json``, which declares
itself synthetic test data.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from xavani_operator.finance.money import incl_to_excl, rands_to_cents, vat_on_excl
from xavani_operator.finance.validation import (
    FinanceValidationError,
    convert_minor_units,
    duplicate_invoices,
    finite_decimal,
    money_minor_units,
    safe_ratio,
    single_currency,
    tax_on_minor_units,
    validate_dcf_rates,
    validate_statement,
    validate_tax_rate,
)

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "business" / "finance_cases.json"


@pytest.fixture(scope="module")
def cases() -> dict:
    data = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    return data["cases"]


# --- fixture self-identification -------------------------------------------------


def test_fixture_declares_itself_synthetic():
    data = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    assert data["synthetic"] is True
    assert data["data_classification"] == "SYNTHETIC TEST DATA"
    assert "NOT company financial data" in data["disclaimer"]


# --- microcycle 1: reject NaN and infinity ---------------------------------------


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity", "nan", 1.2, True, False, None, [], {}])
def test_invalid_financial_values_fail(value):
    with pytest.raises(FinanceValidationError):
        finite_decimal(value)


def test_text_integer_and_decimal_strings_are_accepted():
    assert finite_decimal("100.00") == Decimal("100.00")
    assert finite_decimal(100) == Decimal("100")
    assert finite_decimal(Decimal("0.05")) == Decimal("0.05")


# --- microcycle 2: reject missing currency or period ------------------------------


def test_statement_requires_exact_reconciliation(cases):
    value = cases["balanced_statement"]
    result = validate_statement(value)
    assert result["difference"] == "0"
    assert result["currency"] == "ZAR"
    assert result["period"] == "2026-Q2"
    with pytest.raises(FinanceValidationError):
        validate_statement(cases["unbalanced_statement"])


@pytest.mark.parametrize("case", ["missing_currency_statement", "missing_period_statement"])
def test_statement_requires_currency_and_period(cases, case):
    with pytest.raises(FinanceValidationError):
        validate_statement(cases[case])


def test_statement_rejects_non_object():
    with pytest.raises(FinanceValidationError):
        validate_statement(["not", "a", "statement"])


def test_statement_requires_source(cases):
    with pytest.raises(FinanceValidationError):
        validate_statement({**cases["balanced_statement"], "source": "   "})


# --- microcycle 3: reject mixed currencies without conversion data ----------------


def test_mixed_currencies_rejected_without_conversion_data(cases):
    payload = cases["mixed_currency_rows"]
    with pytest.raises(FinanceValidationError):
        single_currency(payload["rows"])
    with pytest.raises(FinanceValidationError):
        single_currency(payload["rows"], reporting_currency="ZAR")
    with pytest.raises(FinanceValidationError):
        single_currency(payload["rows"], reporting_currency="ZAR", conversions={"EUR>USD": "1.10"})


def test_mixed_currencies_convert_with_explicit_data(cases):
    payload = cases["mixed_currency_rows"]
    rows = payload["rows"]
    conversions = payload["conversions"]
    assert single_currency(rows, reporting_currency="ZAR", conversions=conversions) == "ZAR"
    assert convert_minor_units(5000, source_currency="EUR", target_currency="ZAR", conversions=conversions) == 100000
    assert convert_minor_units(10000, source_currency="ZAR", target_currency="ZAR", conversions=None) == 10000
    total = sum(
        convert_minor_units(row["amount_minor"], source_currency=row["currency"], target_currency="ZAR", conversions=conversions)
        for row in rows
    )
    assert total == 110000


def test_conversion_data_must_be_explicit_and_positive(cases):
    rows = cases["mixed_currency_rows"]["rows"]
    with pytest.raises(FinanceValidationError):
        single_currency(rows, reporting_currency="ZAR", conversions={"EUR>ZAR": "0"})
    with pytest.raises(FinanceValidationError):
        single_currency(rows, reporting_currency="ZAR", conversions={"EUR>ZAR": "NaN"})
    with pytest.raises(FinanceValidationError):
        single_currency(rows, reporting_currency="ZAR", conversions={"EUR>ZAR": 20.0})


def test_single_currency_rows_need_no_conversion(cases):
    rows = cases["duplicate_invoice_rows"]
    assert single_currency(rows) == "ZAR"
    with pytest.raises(FinanceValidationError):
        single_currency([])
    with pytest.raises(FinanceValidationError):
        single_currency([{"currency": ""}])


# --- microcycle 4: reject an unbalanced statement ---------------------------------


def test_unbalanced_statement_reports_the_difference(cases):
    with pytest.raises(FinanceValidationError, match="does not balance"):
        validate_statement(cases["unbalanced_statement"])


def test_missing_statement_amount_is_rejected(cases):
    with pytest.raises(FinanceValidationError):
        validate_statement({**cases["balanced_statement"], "equity": None})


# --- microcycle 5: reject duplicate invoice identity ------------------------------


def test_duplicate_invoice_identity(cases):
    rows = cases["duplicate_invoice_rows"]
    assert duplicate_invoices(rows) == ("INV-1",)
    assert duplicate_invoices(rows[:1]) == ()


def test_incomplete_invoice_identity_is_rejected():
    row = {"supplier_id": "supplier-1", "invoice_number": "INV-1", "currency": "ZAR"}
    with pytest.raises(FinanceValidationError):
        duplicate_invoices([{**row, "currency": ""}])
    with pytest.raises(FinanceValidationError):
        duplicate_invoices([{"supplier_id": "supplier-1", "currency": "ZAR"}])


def test_same_invoice_number_across_suppliers_is_not_a_duplicate(cases):
    rows = cases["duplicate_invoice_rows"]
    assert duplicate_invoices([rows[0], rows[2]]) == ()


# --- microcycle 6: zero denominator is unavailable, not zero ----------------------


def test_zero_denominator_is_unavailable(cases):
    subject = cases["zero_denominator_ratio"]
    assert safe_ratio(subject["numerator"], subject["denominator"]) is None
    assert safe_ratio("10", "-0") is None
    assert safe_ratio("10", "0.00") is None


def test_nonzero_denominator_returns_a_decimal_string():
    assert safe_ratio("10", "4") == "2.5"
    with pytest.raises(FinanceValidationError):
        safe_ratio("10", "NaN")


# --- microcycle 7: perpetual DCF needs discount_rate > terminal_growth ------------


def test_invalid_terminal_growth_fails(cases):
    rates = cases["dcf_rates"]
    with pytest.raises(FinanceValidationError):
        validate_dcf_rates(rates["perpetuity_undefined"]["discount_rate"], rates["perpetuity_undefined"]["terminal_growth"])
    with pytest.raises(FinanceValidationError):
        validate_dcf_rates("0.04", "0.08")


def test_valid_dcf_rates_pass(cases):
    rates = cases["dcf_rates"]["valid"]
    discount, growth = validate_dcf_rates(rates["discount_rate"], rates["terminal_growth"])
    assert (discount, growth) == (Decimal("0.12"), Decimal("0.04"))
    with pytest.raises(FinanceValidationError):
        validate_dcf_rates("0.12", "Infinity")


# --- microcycle 8: money stays integer minor units or Decimal strings -------------


def test_money_is_integer_minor_units():
    assert money_minor_units(10000) == 10000
    assert money_minor_units("10000") == 10000
    assert money_minor_units(Decimal("10000.00")) == 10000
    with pytest.raises(FinanceValidationError):
        money_minor_units(100.5)
    with pytest.raises(FinanceValidationError):
        money_minor_units("100.50")
    with pytest.raises(FinanceValidationError):
        money_minor_units(True)
    with pytest.raises(FinanceValidationError):
        money_minor_units("NaN")


# --- microcycle 9: negatives retained where the schema permits --------------------


def test_negative_values_are_retained():
    assert finite_decimal("-0.05") == Decimal("-0.05")
    assert money_minor_units(-500) == -500
    assert safe_ratio("-10", "4") == "-2.5"
    assert tax_on_minor_units(-10000, rate="0.15", jurisdiction="ZA") == -1500


def test_balanced_negative_equity_statement_is_accepted(cases):
    assert validate_statement(cases["negative_equity_statement"])["difference"] == "0"


# --- microcycle 10: tax needs an explicit rate and jurisdiction -------------------


def test_tax_requires_rate_and_jurisdiction(cases):
    tax = cases["tax"]
    rate, jurisdiction = validate_tax_rate(tax["valid"]["rate"], tax["valid"]["jurisdiction"])
    assert (rate, jurisdiction) == (Decimal("0.15"), "ZA")
    with pytest.raises(FinanceValidationError):
        validate_tax_rate(tax["missing_rate"]["rate"], tax["missing_rate"]["jurisdiction"])
    with pytest.raises(FinanceValidationError):
        validate_tax_rate(tax["missing_jurisdiction"]["rate"], tax["missing_jurisdiction"]["jurisdiction"])
    with pytest.raises(FinanceValidationError):
        validate_tax_rate("0.15", None)


def test_tax_rate_must_be_a_fraction_and_finite():
    with pytest.raises(FinanceValidationError):
        validate_tax_rate("15", "ZA")
    with pytest.raises(FinanceValidationError):
        validate_tax_rate("Infinity", "ZA")
    with pytest.raises(FinanceValidationError):
        validate_tax_rate(0.15, "ZA")
    with pytest.raises(FinanceValidationError):
        validate_tax_rate(True, "ZA")


def test_tax_amount_rounds_half_up():
    assert tax_on_minor_units(3333, rate="0.15", jurisdiction="ZA") == 500
    assert tax_on_minor_units(0, rate="0", jurisdiction="ZA") == 0
    with pytest.raises(FinanceValidationError):
        tax_on_minor_units(3333, rate="0.15", jurisdiction="")


# --- money.py defects proven by these tests (Task 18 microcycle 1) ----------------


def test_money_rejects_bad_input_as_value_error():
    for value in ("abc", "NaN", "Infinity", "-Infinity", None, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            rands_to_cents(value)


def test_vat_rate_must_be_finite_and_non_negative():
    # decimal.InvalidOperation is an ArithmeticError, not a ValueError; leaking it
    # breaks callers that handle bad input with ``except ValueError``.
    for rate in ("abc", "NaN", "Infinity", -15, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            vat_on_excl(10000, rate)
        with pytest.raises(ValueError):
            incl_to_excl(10000, rate)
