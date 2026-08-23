#!/usr/bin/env python3

# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.

"""Tests for the persistent todo store (Task 2.1)."""

import json
import os
import stat

import pytest

from tools.persistent_todo import PersistentTodoStore


@pytest.fixture
def store_path(tmp_path):
    return tmp_path / "todos.json"


def _items(*triples):
    return [
        {"id": i, "content": c, "status": s} for (i, c, s) in triples
    ]


class TestRoundTrip:
    def test_write_persists_to_disk(self, store_path):
        PersistentTodoStore(store_path).write(_items(("1", "alpha", "pending")))
        data = json.loads(store_path.read_text(encoding="utf-8"))
        assert data["items"][0]["id"] == "1"

    def test_new_instance_loads_previous_state(self, store_path):
        first = PersistentTodoStore(store_path)
        first.write(_items(("1", "alpha", "completed"), ("2", "beta", "pending")))
        second = PersistentTodoStore(store_path)
        assert [i["id"] for i in second.read()] == ["1", "2"]
        assert second.read()[0]["status"] == "completed"

    def test_list_order_is_priority(self, store_path):
        store = PersistentTodoStore(store_path)
        store.write(_items(("a", "first", "pending"), ("b", "second", "pending")))
        store.reorder(["b", "a"])
        again = PersistentTodoStore(store_path)
        assert [i["id"] for i in again.read()] == ["b", "a"]


class TestReorder:
    def test_unknown_ids_ignored(self, store_path):
        store = PersistentTodoStore(store_path)
        store.write(_items(("a", "x", "pending"), ("b", "y", "pending")))
        out = store.reorder(["b", "zzz-unknown", "a"])
        # Unknown ids were never written; they cannot appear in the list.
        assert [i["id"] for i in out] == ["b", "a"]

    def test_reorder_persists(self, store_path):
        store = PersistentTodoStore(store_path)
        store.write(_items(("a", "x", "pending")))
        store.reorder(["a"])
        assert json.loads(store_path.read_text(encoding="utf-8"))["items"]


class TestSetStatus:
    def test_set_status_updates_and_persists(self, store_path):
        store = PersistentTodoStore(store_path)
        store.write(_items(("1", "task", "pending")))
        updated = store.set_status("1", "completed")
        assert updated is not None
        assert updated["status"] == "completed"
        assert (
            PersistentTodoStore(store_path).read()[0]["status"] == "completed"
        )

    def test_invalid_status_returns_none(self, store_path):
        store = PersistentTodoStore(store_path)
        assert store.set_status("1", "exploded") is None

    def test_unknown_id_returns_none(self, store_path):
        store = PersistentTodoStore(store_path)
        assert store.set_status("ghost", "pending") is None


class TestFileSafety:
    def test_file_mode_is_0600(self, store_path):
        PersistentTodoStore(store_path).write(_items(("1", "secret task", "pending")))
        assert stat.S_IMODE(store_path.stat().st_mode) == 0o600

    def test_corrupt_file_loads_as_empty(self, store_path):
        store_path.write_text("{not json", encoding="utf-8")
        assert PersistentTodoStore(store_path).read() == []

    def test_missing_parent_dirs_created(self, tmp_path):
        deep = tmp_path / "a" / "b" / "todos.json"
        PersistentTodoStore(deep).write(_items(("1", "x", "pending")))
        assert deep.exists()

    def test_no_tmp_leftovers_after_write(self, tmp_path):
        store = PersistentTodoStore(tmp_path / "todos.json")
        store.write(_items(("1", "x", "pending")))
        leftovers = [
            p for p in tmp_path.iterdir()
            if p.is_file() and p.name != "todos.json"
        ]
        assert leftovers == []


class TestMergeAndInjectionCompat:
    def test_merge_mode_persists(self, store_path):
        store = PersistentTodoStore(store_path)
        store.write(_items(("1", "alpha", "in_progress")))
        store.write(_items(("2", "beta", "pending")), merge=True)
        again = PersistentTodoStore(store_path)
        ids = {i["id"]: i["status"] for i in again.read()}
        assert ids == {"1": "in_progress", "2": "pending"}

    def test_format_for_injection_skips_completed(self, store_path):
        store = PersistentTodoStore(store_path)
        store.write(_items(("1", "done thing", "completed"), ("2", "open thing", "pending")))
        text = store.format_for_injection()
        assert text is not None
        assert "done thing" not in text
        assert "open thing" in text


class TestDefaultPath:
    def test_default_path_uses_xavani_home(self, monkeypatch, tmp_path):
        monkeypatch.setenv("XAVANI_HOME", str(tmp_path))
        import importlib

        import tools.persistent_todo as mod

        importlib.reload(mod)
        assert mod.DEFAULT_PATH == tmp_path / "todos.json"
        monkeypatch.setenv("XAVANI_HOME", os.environ.get("HOME", "/tmp") + "/.xavani-nonexistent-probe")
        importlib.reload(mod)
