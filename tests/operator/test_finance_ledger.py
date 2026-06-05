# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the finance ledger (v0.7.0 operator M-Biz finance)."""

from __future__ import annotations

from xavani_operator.finance.ledger import Ledger, LedgerEntry
from xavani_operator.finance.money import rands_to_cents, vat_on_excl
from xavani_operator.state import OperatorState


def _income(amount_excl, category="sales", eid="i1", date="2026-06-01"):
    excl = rands_to_cents(amount_excl)
    vat = vat_on_excl(excl)
    return LedgerEntry(id=eid, date=date, kind="income", amount_cents=excl + vat, vat_cents=vat, category=category, party="Client")


def _expense(amount_excl, category="rent", eid="x1", date="2026-06-02"):
    excl = rands_to_cents(amount_excl)
    vat = vat_on_excl(excl)
    return LedgerEntry(id=eid, date=date, kind="expense", amount_cents=excl + vat, vat_cents=vat, category=category)


def test_add_and_list_round_trips(tmp_path):
    led = Ledger(OperatorState(root=tmp_path))
    led.add(_income(100))
    entries = led.entries()
    assert len(entries) == 1
    assert entries[0].category == "sales"
    assert entries[0].kind == "income"


def test_totals_and_vat_due(tmp_path):
    led = Ledger(OperatorState(root=tmp_path))
    led.add(_income(100, eid="i1"))     # excl 10000, vat 1500, incl 11500
    led.add(_expense(50, eid="x1"))     # excl 5000,  vat 750,  incl 5750
    t = led.totals()
    assert t["income"] == 11500
    assert t["expense"] == 5750
    assert t["net"] == 11500 - 5750
    assert t["vat_output"] == 1500
    assert t["vat_input"] == 750
    assert t["vat_due"] == 1500 - 750


def test_by_category(tmp_path):
    led = Ledger(OperatorState(root=tmp_path))
    led.add(_income(100, category="sales", eid="i1"))
    led.add(_expense(50, category="rent", eid="x1"))
    bc = led.by_category()
    assert bc["sales"]["income"] == 11500
    assert bc["rent"]["expense"] == 5750
