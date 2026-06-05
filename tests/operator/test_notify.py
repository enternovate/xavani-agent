# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for approval delivery / notification (v0.7.0 operator U30)."""

from __future__ import annotations

from xavani_operator.config import ProductConfig, ProductInfo
from xavani_operator.notify import deliver_approval_request, format_approval_request
from xavani_operator.propose import make_proposal
from xavani_operator.types import Intent, Opportunity


def _proposal():
    intent = Intent(opportunity=Opportunity(id="o", kind="announce", workstream="promote", score=0.6, rationale="ship it"))
    return make_proposal(intent, proposal_id="p1")


def _cfg():
    return ProductConfig(product=ProductInfo(name="Acme"))


def test_format_includes_product_steps_and_actions():
    msg = format_approval_request(_proposal(), _cfg())
    assert "Acme" in msg
    assert "p1" in msg
    assert "post_external" in msg  # a step action class
    assert "APPROVE" in msg        # tier name shown
    assert "approve" in msg.lower()  # instructions


def test_deliver_calls_sender_and_reports():
    sent = []
    ok = deliver_approval_request(_proposal(), _cfg(), sender=sent.append)
    assert ok is True
    assert sent and "Acme" in sent[0]


def test_deliver_without_sender_returns_false():
    assert deliver_approval_request(_proposal(), _cfg()) is False
