# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""B14: hierarchical memory tests."""

import time

import pytest

from tools.hierarchical_memory import (
    PROMOTION_SUCCESSES,
    WORKING_TTL_SECONDS,
    HierarchicalMemory,
)


@pytest.fixture
def hm(tmp_path):
    return HierarchicalMemory(home=tmp_path)


# ── working tier ───────────────────────────────────────────────────


def test_working_store_and_recall(hm):
    hm.store_working("s1", "fixing auth bug")
    assert hm.working("s1") == "fixing auth bug"


def test_working_unknown_session(hm):
    assert hm.working("ghost") is None


def test_working_expires(hm, monkeypatch):
    hm.store_working("s1", "old context")
    future = time.time() + WORKING_TTL_SECONDS + 60
    monkeypatch.setattr("tools.hierarchical_memory.time.time", lambda: future)
    assert hm.working("s1") is None


# ── episodic tier ──────────────────────────────────────────────────


def test_episodic_success_counts(hm):
    hm.store_episodic("task:auth", outcome="success")
    hm.store_episodic("task:auth", outcome="success")
    entry = hm.episodic("task:auth")
    assert entry["successes"] == 2


def test_episodic_failure_counts(hm):
    hm.store_episodic("task:x", outcome="failure")
    entry = hm.episodic("task:x")
    assert entry["failures"] == 1
    assert entry["successes"] == 0


def test_episodic_unknown(hm):
    assert hm.episodic("ghost") is None


def test_episodic_note_updated(hm):
    hm.store_episodic("task:x", outcome="success", note="first")
    hm.store_episodic("task:x", outcome="success", note="second")
    assert hm.episodic("task:x")["note"] == "second"


# ── promotion ──────────────────────────────────────────────────────


def test_no_promotion_below_threshold(hm):
    hm.store_episodic("task:x", outcome="success")
    assert hm.promote_if_ready("task:x") is False
    assert hm.procedural("task:x") is None


def test_promotion_after_successes(hm):
    for _ in range(PROMOTION_SUCCESSES):
        hm.store_episodic("task:x", outcome="success")
    assert hm.promote_if_ready("task:x") is True
    # Moved to procedural; dropped from episodic.
    assert hm.procedural("task:x") is not None
    assert hm.episodic("task:x") is None


def test_promotion_unknown_key(hm):
    assert hm.promote_if_ready("ghost") is False


def test_failures_never_promote(hm):
    for _ in range(5):
        hm.store_episodic("task:x", outcome="failure")
    assert hm.promote_if_ready("task:x") is False


def test_all_procedural(hm):
    for _ in range(PROMOTION_SUCCESSES):
        hm.store_episodic("task:a", outcome="success")
    hm.promote_if_ready("task:a")
    keys = [p["key"] for p in hm.all_procedural()]
    assert keys == ["task:a"]


# ── state ──────────────────────────────────────────────────────────


def test_tier_counts(hm):
    hm.store_working("s1", "context")
    hm.store_episodic("task:x", outcome="success")
    counts = hm.tier_counts()
    assert counts["working"] == 1
    assert counts["episodic"] == 1
    assert counts["procedural"] == 0


def test_persists_across_instances(tmp_path):
    hm1 = HierarchicalMemory(home=tmp_path)
    hm1.store_episodic("task:x", outcome="success")
    hm2 = HierarchicalMemory(home=tmp_path)
    assert hm2.episodic("task:x") is not None


def test_snapshot_shape(hm):
    hm.store_working("s1", "ctx")
    snap = hm.snapshot()
    assert set(snap.keys()) == {"working", "episodic", "procedural"}
