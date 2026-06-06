# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the finance audit/reconcile report (v0.7.0 operator M-Biz finance)."""

from __future__ import annotations

from xavani_operator.finance.audit import audit, render_audit
from xavani_operator.finance.ledger import Ledger, LedgerEntry
from xavani_operator.finance.money import rands_to_cents, vat_on_excl
from xavani_operator.state import OperatorState


def _entry(kind, amount_excl, eid, category="sales", ref="", paid=True, amount_cents=None):
    if amount_cents is None:
        excl = rands_to_cents(amount_excl)
        vat = vat_on_excl(excl)
        amount_cents = excl + vat
    else:
        vat = 0
    return LedgerEntry(id=eid, date="2026-06-01", kind=kind, amount_cents=amount_cents, vat_cents=vat, category=category, ref=ref, paid=paid)


def test_audit_totals_and_vat(tmp_path):
    led = Ledger(OperatorState(root=tmp_path))
    led.add(_entry("income", 100, "i1"))
    led.add(_entry("expense", 50, "x1", category="rent"))
    r = audit(led)
    assert r["income"] == 11500
    assert r["vat_due"] == 1500 - 750
    assert r["entries"] == 2


def test_audit_flags_uncategorized(tmp_path):
    led = Ledger(OperatorState(root=tmp_path))
    led.add(_entry("expense", 50, "x1", category="uncategorized"))
    assert audit(led)["uncategorized"] == 1


def test_audit_flags_duplicate_refs_and_negatives(tmp_path):
    led = Ledger(OperatorState(root=tmp_path))
    led.add(_entry("income", 100, "i1", ref="INV-1"))
    led.add(_entry("income", 100, "i2", ref="INV-1"))          # duplicate ref
    led.add(_entry("expense", 0, "x1", amount_cents=-500))      # negative
    r = audit(led)
    assert "INV-1" in r["duplicate_refs"]
    assert r["anomalies"] >= 2


def test_audit_counts_unpaid(tmp_path):
    led = Ledger(OperatorState(root=tmp_path))
    led.add(_entry("income", 100, "i1", paid=False))
    assert audit(led)["unpaid"] == 1


def test_render_audit_is_readable(tmp_path):
    led = Ledger(OperatorState(root=tmp_path))
    led.add(_entry("income", 100, "i1"))
    text = render_audit(audit(led))
    assert "VAT" in text
    assert "due" in text.lower()
