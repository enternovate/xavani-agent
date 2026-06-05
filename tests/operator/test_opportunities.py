# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the deterministic opportunity rule engine (v0.7.0 operator U15–U18)."""

from __future__ import annotations

from xavani_operator.config import Channel, Goal, ProductConfig, ProductInfo
from xavani_operator.opportunities import (
    build_opportunities,
    detect,
    ops_opportunities,
    promote_opportunities,
)
from xavani_operator.types import Perception


def _cfg(**kw) -> ProductConfig:
    return ProductConfig(product=ProductInfo(name="X"), **kw)


# --- U16: build rules -------------------------------------------------------

def test_failing_tests_yield_fix_opportunity():
    opps = build_opportunities(Perception(tests={"known": True, "failing": 3}), _cfg())
    fix = next(o for o in opps if o.kind == "fix_tests")
    assert fix.workstream == "build"
    assert fix.score >= 0.7


def test_no_fix_opportunity_when_tests_pass():
    opps = build_opportunities(Perception(tests={"known": True, "failing": 0}), _cfg())
    assert not any(o.kind == "fix_tests" for o in opps)


def test_todos_yield_debt_opportunity():
    p = Perception(issues=[{"marker": "TODO", "file": "a.py", "line": 1, "text": "x"}])
    assert any(o.kind == "address_todos" for o in build_opportunities(p, _cfg()))


def test_goals_yield_build_opportunities_scored_by_priority():
    cfg = _cfg(goals=[Goal(id="g1", intent="ship", priority=1), Goal(id="g2", intent="later", priority=5)])
    opps = build_opportunities(Perception(), cfg)
    g1 = next(o for o in opps if o.payload.get("goal_id") == "g1")
    g2 = next(o for o in opps if o.payload.get("goal_id") == "g2")
    assert g1.score > g2.score


# --- U17: promote rules -----------------------------------------------------

def test_notable_commit_yields_announce():
    p = Perception(repo={"is_git": True, "recent_commits": ["Release v0.7.0"]})
    assert any(o.kind == "announce" for o in promote_opportunities(p, _cfg()))


def test_channels_yield_cadence_content():
    cfg = _cfg(channels=[Channel(platform="x")])
    assert any(o.kind == "cadence_content" for o in promote_opportunities(Perception(), cfg))


def test_no_promote_without_channels_or_notable_commit():
    p = Perception(repo={"recent_commits": ["fix a typo"]})
    assert promote_opportunities(p, _cfg()) == []


# --- U18: ops rules ---------------------------------------------------------

def test_dirty_repo_yields_housekeeping():
    p = Perception(repo={"dirty": True, "dirty_files": 12})
    assert any(o.kind == "housekeeping" for o in ops_opportunities(p, _cfg()))


def test_tidy_repo_has_no_ops_opportunity():
    p = Perception(repo={"dirty": False, "dirty_files": 0})
    assert ops_opportunities(p, _cfg()) == []


# --- U15: engine ------------------------------------------------------------

def test_detect_aggregates_and_sorts_by_score_desc():
    cfg = _cfg(goals=[Goal(id="g1", priority=1)], channels=[Channel(platform="x")])
    opps = detect(Perception(tests={"known": True, "failing": 2}), cfg)
    scores = [o.score for o in opps]
    assert scores == sorted(scores, reverse=True)
    assert len(opps) >= 2


def test_detect_is_deterministic():
    cfg = _cfg(goals=[Goal(id="g1", priority=1), Goal(id="g2", priority=1)])
    first = [o.id for o in detect(Perception(), cfg)]
    second = [o.id for o in detect(Perception(), cfg)]
    assert first == second


def test_detect_quiet_state_is_empty():
    assert detect(Perception(), _cfg()) == []
