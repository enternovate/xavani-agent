"""TDD tests for the edit tool's mode selection (Task 15).

Covers mode resolution order (per-model table -> XAVANI_EDIT_MODE ->
config edit.mode -> default 'patch'), patch-mode delegation to the existing
patch handler, hashline-mode application through the default snapshot store,
replace-mode exact-string substitution, and unknown-mode error handling.
"""

import json

import pytest

import tools.edit_tool as edit_tool
from tools.edit_tool import (
    DEFAULT_EDIT_MODE,
    _handle_edit,
    resolve_edit_mode,
)
from tools.hashline.snapshots import default_store


# ---------------------------------------------------------------------------
# mode resolution
# ---------------------------------------------------------------------------


def test_default_mode_is_patch(monkeypatch, tmp_path):
    monkeypatch.delenv("XAVANI_EDIT_MODE", raising=False)
    monkeypatch.setattr(edit_tool, "get_config_path", lambda: tmp_path / "no-such-config.yaml")
    assert resolve_edit_mode() == "patch"
    assert DEFAULT_EDIT_MODE == "patch"


def test_config_mode_beats_default(monkeypatch, tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("edit:\n  mode: hashline\n", encoding="utf-8")
    monkeypatch.delenv("XAVANI_EDIT_MODE", raising=False)
    monkeypatch.setattr(edit_tool, "get_config_path", lambda: cfg)
    assert resolve_edit_mode() == "hashline"


def test_env_override_beats_config(monkeypatch, tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("edit:\n  mode: hashline\n", encoding="utf-8")
    monkeypatch.setattr(edit_tool, "get_config_path", lambda: cfg)
    monkeypatch.setenv("XAVANI_EDIT_MODE", "replace")
    assert resolve_edit_mode() == "replace"


def test_per_model_table_beats_env(monkeypatch, tmp_path):
    monkeypatch.setenv("XAVANI_EDIT_MODE", "replace")
    monkeypatch.setattr(edit_tool, "get_config_path", lambda: tmp_path / "no-such-config.yaml")
    monkeypatch.setattr(edit_tool, "PER_MODEL_EDIT_MODE", {"claude-sonnet-4-5": "hashline"})
    assert resolve_edit_mode("claude-sonnet-4-5") == "hashline"
    # Unknown model falls through to env.
    assert resolve_edit_mode("some-other-model") == "replace"


# ---------------------------------------------------------------------------
# patch mode delegates to the existing patch handler
# ---------------------------------------------------------------------------


def test_patch_mode_delegates(monkeypatch):
    calls = {}

    def fake_patch_handler(inner_args, task_id=None, **kw):
        calls["args"] = inner_args
        calls["task_id"] = task_id
        return json.dumps({"ok": True, "mode": "patch"})

    monkeypatch.setattr("tools.file_tools._handle_patch", fake_patch_handler)
    payload = "*** Begin Patch\n*** Update File: a.py\n@@ x @@\n-old\n+new\n*** End Patch\n"
    result = _handle_edit({"input": payload, "mode": "patch"}, task_id="t1")
    assert calls["args"] == {"mode": "patch", "patch": payload}
    assert calls["task_id"] == "t1"
    assert json.loads(result)["ok"] is True


# ---------------------------------------------------------------------------
# hashline mode applies through the default snapshot store
# ---------------------------------------------------------------------------


def test_hashline_mode_applies_to_file(monkeypatch, tmp_path):
    monkeypatch.delenv("XAVANI_EDIT_MODE", raising=False)
    monkeypatch.setattr(edit_tool, "get_config_path", lambda: tmp_path / "no-such-config.yaml")

    f = tmp_path / "greet.py"
    f.write_text("a\nb\nc\n", encoding="utf-8")
    # Simulate the read tool's snapshot: record content, then use its tag.
    default_store.record(str(f), "a\nb\nc\n", ranges=((1, 3),))
    tag = default_store.get(str(f)).tag

    payload = f"[{f}#{tag}]\nPUT 2.=3:\n+X\n+Y\n"
    result = _handle_edit({"input": payload, "mode": "hashline"}, task_id="t2")
    data = json.loads(result)
    assert data.get("ok") is True, data
    assert data["mode"] == "hashline"
    assert f.read_text(encoding="utf-8") == "a\nX\nY\n"


def test_hashline_parse_error_returns_error_string(tmp_path):
    result = _handle_edit({"input": "this is not a hashline payload\n", "mode": "hashline"})
    data = json.loads(result)
    assert "error" in data
    assert "hashline" in data["error"]


# ---------------------------------------------------------------------------
# replace mode: exact-string substitution
# ---------------------------------------------------------------------------


def test_replace_mode_exact_string(tmp_path):
    f = tmp_path / "note.txt"
    f.write_text("hello world\n", encoding="utf-8")
    result = _handle_edit(
        {"mode": "replace", "path": str(f), "old_string": "world", "new_string": "there"},
        task_id="t3",
    )
    data = json.loads(result)
    assert data.get("ok") is True, data
    assert f.read_text(encoding="utf-8") == "hello there\n"


def test_replace_mode_missing_old_string_returns_error(tmp_path):
    f = tmp_path / "note.txt"
    f.write_text("hello world\n", encoding="utf-8")
    result = _handle_edit(
        {"mode": "replace", "path": str(f), "old_string": "nope", "new_string": "x"},
        task_id="t4",
    )
    data = json.loads(result)
    assert "error" in data


# ---------------------------------------------------------------------------
# unknown mode
# ---------------------------------------------------------------------------


def test_unknown_mode_returns_error():
    result = _handle_edit({"input": "x", "mode": "bogus"})
    data = json.loads(result)
    assert "error" in data
    assert "bogus" in data["error"]
