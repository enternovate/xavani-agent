# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for decide (U19) and the Workstream protocol/registry (U20)."""

from __future__ import annotations

from xavani_operator.config import ProductConfig, ProductInfo
from xavani_operator.decide import decide
from xavani_operator.types import Opportunity
from xavani_operator.workstreams.base import (
    Workstream,
    all_workstreams,
    clear_workstreams,
    get_workstream,
    register_workstream,
)


def _cfg() -> ProductConfig:
    return ProductConfig(product=ProductInfo(name="X"))


# --- U19: decide ------------------------------------------------------------

def test_decide_returns_none_for_no_opportunities():
    assert decide([], _cfg()) is None


def test_decide_picks_highest_score():
    a = Opportunity(id="a", kind="k", workstream="build", score=0.3)
    b = Opportunity(id="b", kind="k", workstream="build", score=0.9)
    intent = decide([a, b], _cfg())
    assert intent.opportunity.id == "b"


def test_decide_tie_break_lowest_id():
    a = Opportunity(id="a", kind="k", workstream="build", score=0.5)
    b = Opportunity(id="b", kind="k", workstream="build", score=0.5)
    assert decide([b, a], _cfg()).opportunity.id == "a"


# --- U20: Workstream protocol + registry -----------------------------------

class _DummyWS:
    name = "dummy"

    def detect_opportunities(self, perception, config):
        return []

    def make_plan(self, intent, ctx):
        return None

    def execute(self, step, ctx):
        return None

    def verify(self, result, ctx):
        return None


def test_register_and_get_workstream():
    clear_workstreams()
    ws = _DummyWS()
    register_workstream(ws)
    assert get_workstream("dummy") is ws
    assert "dummy" in all_workstreams()


def test_get_unknown_returns_none():
    clear_workstreams()
    assert get_workstream("nope") is None


def test_dummy_satisfies_workstream_protocol():
    assert isinstance(_DummyWS(), Workstream)
