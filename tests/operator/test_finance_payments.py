# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for SA payment-instruction generation (v0.7.0 operator M-Biz finance).

The agent INSTRUCTS payments (the user executes) — it never moves money.
"""

from __future__ import annotations

import pytest

from xavani_operator.finance.payments import (
    eft_instruction,
    payment_link_instruction,
    render_instruction,
)


def test_eft_instruction():
    instr = eft_instruction("Acme Supplies", "1234567890", "250655", 250000, "INV-001", bank="FNB")
    assert instr["method"] == "eft"
    assert instr["amount"] == "R2,500.00"
    assert instr["beneficiary"] == "Acme Supplies"
    assert instr["reference"] == "INV-001"
    assert "you" in instr["action"].lower()  # the human pays


def test_payment_link_rails():
    for rail in ["payfast", "yoco", "ozow", "snapscan"]:
        instr = payment_link_instruction(rail, 10000, "REF-9")
        assert instr["method"] == "payment_link"
        assert instr["rail"] == rail
        assert instr["amount"] == "R100.00"


def test_unsupported_rail_rejected():
    with pytest.raises(ValueError):
        payment_link_instruction("paypal", 100, "R")


def test_render_eft_is_human_readable():
    text = render_instruction(eft_instruction("X Co", "1", "2", 250000, "REF"))
    assert "Pay R2,500.00" in text
    assert "REF" in text


def test_render_payment_link():
    text = render_instruction(payment_link_instruction("yoco", 10000, "REF"))
    assert "yoco" in text
    assert "Pay R100.00" in text
