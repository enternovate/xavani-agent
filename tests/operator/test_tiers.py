# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the deterministic approval-tier classifier (v0.7.0 operator U4)."""

from __future__ import annotations

from xavani_operator.tiers import classify
from xavani_operator.types import Tier


def test_local_actions_are_auto():
    assert classify("run_tests") == Tier.AUTO
    assert classify("read") == Tier.AUTO
    assert classify("commit_workbranch") == Tier.AUTO


def test_low_risk_actions_notify():
    assert classify("open_draft_pr") == Tier.NOTIFY
    assert classify("create_issue") == Tier.NOTIFY


def test_outward_or_costly_actions_require_approval():
    assert classify("post_external") == Tier.APPROVE
    assert classify("deploy") == Tier.APPROVE
    assert classify("send_external") == Tier.APPROVE


def test_destructive_actions_are_blocked():
    assert classify("force_push") == Tier.BLOCK
    assert classify("payment") == Tier.BLOCK


def test_unknown_action_defaults_to_approve_conservatively():
    # Fail safe: anything we don't recognise needs a human.
    assert classify("some_brand_new_action") == Tier.APPROVE


def test_overrides_can_raise_or_lower_a_tier():
    assert classify("post_external", overrides={"post_external": 1}) == Tier.NOTIFY
    assert classify("run_tests", overrides={"run_tests": 2}) == Tier.APPROVE


def test_override_accepts_tier_enum_or_int():
    assert classify("deploy", overrides={"deploy": Tier.BLOCK}) == Tier.BLOCK
