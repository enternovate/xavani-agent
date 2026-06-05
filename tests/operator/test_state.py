# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the persistent operator state store (v0.7.0 operator U3)."""

from __future__ import annotations

import pytest

from xavani_operator.state import OperatorState, default_operator_dir


def test_put_then_get_round_trips(tmp_path):
    s = OperatorState(root=tmp_path)
    s.put("proposals", "p1", {"id": "p1", "status": "pending", "steps": [1, 2]})
    assert s.get("proposals", "p1") == {"id": "p1", "status": "pending", "steps": [1, 2]}


def test_get_missing_returns_none(tmp_path):
    s = OperatorState(root=tmp_path)
    assert s.get("proposals", "nope") is None


def test_put_overwrites(tmp_path):
    s = OperatorState(root=tmp_path)
    s.put("c", "k", {"v": 1})
    s.put("c", "k", {"v": 2})
    assert s.get("c", "k") == {"v": 2}


def test_list_returns_all_in_stable_order(tmp_path):
    s = OperatorState(root=tmp_path)
    s.put("proposals", "p2", {"id": "p2"})
    s.put("proposals", "p1", {"id": "p1"})
    s.put("proposals", "p3", {"id": "p3"})
    assert [d["id"] for d in s.list("proposals")] == ["p1", "p2", "p3"]


def test_list_empty_collection_is_empty(tmp_path):
    s = OperatorState(root=tmp_path)
    assert s.list("nothing") == []


def test_delete_removes_and_reports(tmp_path):
    s = OperatorState(root=tmp_path)
    s.put("c", "k", {"v": 1})
    assert s.delete("c", "k") is True
    assert s.get("c", "k") is None
    assert s.delete("c", "k") is False


def test_persists_across_instances(tmp_path):
    OperatorState(root=tmp_path).put("c", "k", {"v": 42})
    assert OperatorState(root=tmp_path).get("c", "k") == {"v": 42}


def test_unsafe_keys_are_rejected(tmp_path):
    s = OperatorState(root=tmp_path)
    for bad in ["..", ".", "a/b", "../escape", "x\\y"]:
        with pytest.raises(ValueError):
            s.put("c", bad, {"v": 1})


def test_default_operator_dir_under_xavani_home():
    from xavani_constants import get_xavani_home

    d = default_operator_dir()
    assert d.name == "operator"
    # The operator dir always lives directly under the active Xavani home
    # (profile-aware; the test harness points XAVANI_HOME at a temp dir).
    assert d.parent == get_xavani_home()
