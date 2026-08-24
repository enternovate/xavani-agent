# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for tools/checkpoint_tool.py — the model-invocable checkpoint tool."""

import json
import shutil
from pathlib import Path

import pytest

from tools.checkpoint_manager import CheckpointManager
from tools.checkpoint_tool import (
    checkpoint_tool,
    set_checkpoint_manager,
)
from tools.registry import registry

GIT_AVAILABLE = shutil.which("git") is not None


# =========================================================================
# Fixtures
# =========================================================================

@pytest.fixture()
def work_dir(tmp_path):
    d = tmp_path / "project"
    d.mkdir()
    (d / "main.py").write_text("print('v1')\n", encoding="utf-8")
    (d / "notes.txt").write_text("notes v1\n", encoding="utf-8")
    return d


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    """Isolated checkpoint base + fake home — never touches ~/.xavani/."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.delenv("HOMEDRIVE", raising=False)
    monkeypatch.delenv("HOMEPATH", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.setattr(
        "tools.checkpoint_manager.CHECKPOINT_BASE", tmp_path / "checkpoints"
    )
    yield
    set_checkpoint_manager(None)


@pytest.fixture()
def enabled_manager():
    mgr = CheckpointManager(enabled=True, max_snapshots=50)
    set_checkpoint_manager(mgr)
    return mgr


@pytest.fixture()
def disabled_manager():
    mgr = CheckpointManager(enabled=False)
    set_checkpoint_manager(mgr)
    return mgr


def _run(args):
    return json.loads(checkpoint_tool(args))


# =========================================================================
# Registry wiring
# =========================================================================

class TestRegistryRegistration:
    def test_registered_with_expected_metadata(self):
        entry = registry.get_entry("checkpoint")
        assert entry is not None
        assert entry.toolset == "file"
        assert entry.emoji == "⏮️"
        assert entry.max_result_size_chars == 20_000
        assert callable(entry.handler)
        assert callable(entry.check_fn)

    def test_schema_exposes_action_enum_and_optional_params(self):
        entry = registry.get_entry("checkpoint")
        assert entry is not None
        params = entry.schema["parameters"]
        assert params["required"] == ["action"]
        props = params["properties"]
        assert props["action"]["enum"] == ["create", "list", "diff", "restore"]
        for optional in ("working_dir", "commit_hash", "file_path", "reason"):
            assert optional in props

    def test_check_fn_returns_true(self):
        entry = registry.get_entry("checkpoint")
        assert entry is not None
        assert entry.check_fn() is True


# =========================================================================
# create
# =========================================================================

@pytest.mark.skipif(not GIT_AVAILABLE, reason="git not available")
class TestCreate:
    def test_create_takes_checkpoint(self, work_dir, enabled_manager):
        result = _run(
            {"action": "create", "working_dir": str(work_dir), "reason": "before refactor"}
        )
        assert result["success"] is True
        assert result["checkpoint_taken"] is True
        assert result["enabled"] is True
        assert result["working_dir"] == str(work_dir)
        assert result["checkpoint"]["reason"] == "before refactor"
        assert len(enabled_manager.list_checkpoints(str(work_dir))) == 1

    def test_create_disabled_manager_reports_not_taken(self, work_dir, disabled_manager):
        result = _run({"action": "create", "working_dir": str(work_dir)})
        assert result["success"] is True
        assert result["checkpoint_taken"] is False
        assert result["enabled"] is False
        assert "checkpoint" not in result


# =========================================================================
# list
# =========================================================================

class TestList:
    def test_list_empty_store(self, work_dir, enabled_manager):
        result = _run({"action": "list", "working_dir": str(work_dir)})
        assert result["success"] is True
        assert result["checkpoints"] == []
        assert result["count"] == 0

    @pytest.mark.skipif(not GIT_AVAILABLE, reason="git not available")
    def test_lists_created_checkpoints_newest_first(self, work_dir, enabled_manager):
        _run({"action": "create", "working_dir": str(work_dir), "reason": "first"})
        (work_dir / "main.py").write_text("print('v2')\n", encoding="utf-8")
        _run({"action": "create", "working_dir": str(work_dir), "reason": "second"})

        result = _run({"action": "list", "working_dir": str(work_dir)})
        assert result["success"] is True
        assert result["count"] == 2
        reasons = [cp["reason"] for cp in result["checkpoints"]]
        assert reasons == ["second", "first"]
        for cp in result["checkpoints"]:
            for key in ("hash", "short_hash", "timestamp", "files_changed"):
                assert key in cp


# =========================================================================
# diff
# =========================================================================

@pytest.mark.skipif(not GIT_AVAILABLE, reason="git not available")
class TestDiff:
    def test_diff_shows_working_tree_changes(self, work_dir, enabled_manager):
        created = _run({"action": "create", "working_dir": str(work_dir)})
        commit_hash = created["checkpoint"]["hash"]

        (work_dir / "main.py").write_text("print('changed')\n", encoding="utf-8")

        result = _run(
            {"action": "diff", "working_dir": str(work_dir), "commit_hash": commit_hash}
        )
        assert result["success"] is True
        assert "main.py" in result["diff"]["stat"]
        assert "print('changed')" in result["diff"]["diff"]

    def test_diff_requires_commit_hash(self, work_dir, enabled_manager):
        result = _run({"action": "diff", "working_dir": str(work_dir)})
        assert result["success"] is False
        assert "commit_hash" in result["error"]

    def test_diff_unknown_hash_fails_cleanly(self, work_dir, enabled_manager):
        _run({"action": "create", "working_dir": str(work_dir)})
        result = _run(
            {
                "action": "diff",
                "working_dir": str(work_dir),
                "commit_hash": "deadbeefdead",
            }
        )
        assert result["success"] is False
        assert "error" in result


# =========================================================================
# restore
# =========================================================================

@pytest.mark.skipif(not GIT_AVAILABLE, reason="git not available")
class TestRestore:
    def test_restore_reverts_whole_directory(self, work_dir, enabled_manager):
        created = _run({"action": "create", "working_dir": str(work_dir)})
        commit_hash = created["checkpoint"]["hash"]

        (work_dir / "main.py").write_text("print('v2')\n", encoding="utf-8")
        (work_dir / "notes.txt").write_text("notes v2\n", encoding="utf-8")

        result = _run(
            {
                "action": "restore",
                "working_dir": str(work_dir),
                "commit_hash": commit_hash,
            }
        )
        assert result["success"] is True
        assert result["restored"]["restored_to"] == commit_hash[:8]
        assert (work_dir / "main.py").read_text(encoding="utf-8") == "print('v1')\n"
        assert (work_dir / "notes.txt").read_text(encoding="utf-8") == "notes v1\n"

    def test_restore_single_file(self, work_dir, enabled_manager):
        created = _run({"action": "create", "working_dir": str(work_dir)})
        commit_hash = created["checkpoint"]["hash"]

        (work_dir / "main.py").write_text("print('v2')\n", encoding="utf-8")
        (work_dir / "notes.txt").write_text("notes v2\n", encoding="utf-8")

        result = _run(
            {
                "action": "restore",
                "working_dir": str(work_dir),
                "commit_hash": commit_hash,
                "file_path": "notes.txt",
            }
        )
        assert result["success"] is True
        assert result["restored"]["file"] == "notes.txt"
        assert (work_dir / "notes.txt").read_text(encoding="utf-8") == "notes v1\n"
        assert (work_dir / "main.py").read_text(encoding="utf-8") == "print('v2')\n"

    def test_restore_requires_commit_hash(self, work_dir, enabled_manager):
        result = _run({"action": "restore", "working_dir": str(work_dir)})
        assert result["success"] is False
        assert "commit_hash" in result["error"]


# =========================================================================
# Handler contract
# =========================================================================

class TestHandlerContract:
    @pytest.mark.parametrize("args", [
        {"action": "create"},
        {"action": "list"},
        {"action": "diff", "commit_hash": "deadbeefdead"},
        {"action": "restore", "commit_hash": "deadbeefdead"},
        {},
        None,
    ])
    def test_responses_are_parseable_json_strings(self, args):
        raw = checkpoint_tool(args)
        assert isinstance(raw, str)
        payload = json.loads(raw)
        assert isinstance(payload, dict)
        assert "success" in payload

    def test_missing_action_fails(self):
        payload = json.loads(checkpoint_tool({}))
        assert payload["success"] is False
        assert "error" in payload

    def test_unknown_action_fails(self):
        payload = json.loads(checkpoint_tool({"action": "revert"}))
        assert payload["success"] is False
        assert "create" in payload["error"]

    def test_working_dir_defaults_to_cwd(self, tmp_path, monkeypatch, enabled_manager):
        cwd = tmp_path / "cwd-project"
        cwd.mkdir()
        monkeypatch.chdir(cwd)

        result = _run({"action": "list"})
        assert result["success"] is True
        assert Path(result["working_dir"]).resolve() == cwd.resolve()

    def test_handler_never_raises_on_manager_crash(self, work_dir):
        class ExplodingManager(CheckpointManager):
            def __init__(self):
                super().__init__(enabled=True)

            def new_turn(self):
                raise RuntimeError("boom")

            def ensure_checkpoint(self, working_dir, reason="auto"):
                raise RuntimeError("boom")

            def list_checkpoints(self, working_dir):
                raise RuntimeError("boom")

            def diff(self, working_dir, commit_hash):
                raise RuntimeError("boom")

            def restore(self, working_dir, commit_hash, file_path=None):
                raise RuntimeError("boom")

        set_checkpoint_manager(ExplodingManager())

        for action_args in (
            {"action": "create", "working_dir": str(work_dir)},
            {"action": "list", "working_dir": str(work_dir)},
            {"action": "diff", "working_dir": str(work_dir), "commit_hash": "deadbeefdead"},
            {"action": "restore", "working_dir": str(work_dir), "commit_hash": "deadbeefdead"},
        ):
            payload = json.loads(checkpoint_tool(action_args))
            assert payload["success"] is False
            assert "boom" in payload["error"]
