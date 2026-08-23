#!/usr/bin/env python3

# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.

"""Tests for the outstanding-work ledger (Task 2.2)."""

import json
import stat

import pytest

from xavani_wisdom.outstanding import OutstandingLedger


@pytest.fixture
def ledger(tmp_path):
    return OutstandingLedger(tmp_path / "outstanding.jsonl")


class TestAddAndRead:
    def test_add_returns_numbered_entry(self, ledger):
        entry = ledger.add("ship the release", kind="goal", session_id="s1")
        assert entry["n"] == 1
        assert entry["status"] == "open"
        assert entry["text"] == "ship the release"

    def test_numbers_increment(self, ledger):
        ledger.add("a")
        second = ledger.add("b")
        assert second["n"] == 2

    def test_items_open_only_by_default(self, ledger):
        first = ledger.add("a")
        ledger.add("b")
        ledger.set_status(first["n"], "done")
        open_items = ledger.items()
        assert [e["text"] for e in open_items] == ["b"]

    def test_items_include_closed_flag(self, ledger):
        e = ledger.add("a")
        ledger.set_status(e["n"], "cancelled")
        assert len(ledger.items(include_closed=True)) == 1

    def test_invalid_kind_falls_back_to_goal(self, ledger):
        entry = ledger.add("x", kind="party")
        assert entry["kind"] == "goal"


class TestSetStatus:
    def test_done_closes_item(self, ledger):
        e = ledger.add("finish audit")
        updated = ledger.set_status(e["n"], "done")
        assert updated is not None
        assert updated["status"] == "done"
        assert updated["closed_ts"]
        assert ledger.open_count() == 0

    def test_cancelled_closes_item(self, ledger):
        e = ledger.add("obsolete task")
        ledger.set_status(e["n"], "cancelled")
        assert ledger.items() == []

    def test_invalid_status_returns_none(self, ledger):
        e = ledger.add("x")
        assert ledger.set_status(e["n"], "archived") is None

    def test_unknown_n_returns_none(self, ledger):
        assert ledger.set_status(999, "done") is None


class TestFileSafety:
    def test_file_mode_is_0600(self, tmp_path):
        path = tmp_path / "outstanding.jsonl"
        OutstandingLedger(path).add("private plan")
        assert stat.S_IMODE(path.stat().st_mode) == 0o600

    def test_jsonl_shape(self, tmp_path):
        path = tmp_path / "o.jsonl"
        ledger = OutstandingLedger(path)
        ledger.add("one")
        ledger.add("two")
        lines = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()]
        assert [l["n"] for l in lines] == [1, 2]

    def test_corrupt_lines_skipped(self, tmp_path):
        path = tmp_path / "o.jsonl"
        path.write_text("{bad json\n", encoding="utf-8")
        ledger = OutstandingLedger(path)
        e = ledger.add("fresh")
        assert e["n"] >= 1

    def test_missing_parent_dirs_created(self, tmp_path):
        deep = tmp_path / "x" / "y" / "o.jsonl"
        OutstandingLedger(deep).add("deep item")
        assert deep.exists()
