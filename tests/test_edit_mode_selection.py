"""TDD tests for the edit tool's mode selection (Task 15).

Covers mode resolution order (per-model table -> XAVANI_EDIT_MODE ->
config edit.mode -> default 'patch'), patch-mode delegation to the existing
patch handler, hashline-mode application through the default snapshot store,
replace-mode exact-string substitution, and unknown-mode error handling.
"""

import json
import os

import pytest

import tools.edit_tool as edit_tool
import tools.file_tools as file_tools
from tools.edit_tool import (
    DEFAULT_EDIT_MODE,
    _handle_edit,
    resolve_edit_mode,
)
from tools.hashline.snapshots import compute_tag, default_store


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


def test_hashline_stale_tag_error_returns_fresh_tag(monkeypatch, tmp_path):
    """First-edit loop: on a stale/unknown tag, the error must hand back the
    fresh on-disk tag so the model can re-issue the edit immediately
    (read_file does not emit [path#TAG] tags yet)."""
    monkeypatch.delenv("XAVANI_EDIT_MODE", raising=False)
    monkeypatch.setattr(edit_tool, "get_config_path", lambda: tmp_path / "no-such-config.yaml")

    f = tmp_path / "greet.py"
    f.write_text("a\nb\nc\n", encoding="utf-8")
    fresh_tag = compute_tag("a\nb\nc\n")
    stale_tag = "FFFF" if fresh_tag != "FFFF" else "0000"

    payload = f"[{f}#{stale_tag}]\nPUT 2.=3:\n+X\n+Y\n"
    result = _handle_edit({"input": payload, "mode": "hashline"}, task_id="t6")
    data = json.loads(result)
    assert "error" in data
    # The stale tag alone would be an undocumented error-leak retry: the
    # error must name the exact retryable header with the fresh tag.
    assert f"[{f}#{fresh_tag}]" in data["error"]
    assert "re-issue" in data["error"].lower()


def test_hashline_mode_refuses_sensitive_path(monkeypatch, tmp_path):
    """hashline writes must be rejected for sensitive paths, like patch."""
    f = tmp_path / "note.txt"
    f.write_text("a\nb\nc\n", encoding="utf-8")
    monkeypatch.setattr(
        file_tools,
        "_SENSITIVE_PATH_PREFIXES",
        file_tools._SENSITIVE_PATH_PREFIXES + (str(tmp_path) + os.sep,),
    )
    result = _handle_edit(
        {"input": f"[{f}#DEAD]\nPUT 2.=3:\n+X\n", "mode": "hashline"},
        task_id="t7",
    )
    data = json.loads(result)
    assert "error" in data
    assert "sensitive" in data["error"].lower()
    assert f.read_text(encoding="utf-8") == "a\nb\nc\n"


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


def test_replace_mode_refuses_sensitive_path(monkeypatch, tmp_path):
    """replace writes must be rejected for sensitive paths, like patch."""
    f = tmp_path / "note.txt"
    f.write_text("hello world\n", encoding="utf-8")
    monkeypatch.setattr(
        file_tools,
        "_SENSITIVE_PATH_PREFIXES",
        file_tools._SENSITIVE_PATH_PREFIXES + (str(tmp_path) + os.sep,),
    )
    result = _handle_edit(
        {"mode": "replace", "path": str(f), "old_string": "world", "new_string": "there"},
        task_id="t5",
    )
    data = json.loads(result)
    assert "error" in data
    assert "sensitive" in data["error"].lower()
    assert f.read_text(encoding="utf-8") == "hello world\n"


# ---------------------------------------------------------------------------
# unknown mode
# ---------------------------------------------------------------------------


def test_unknown_mode_returns_error():
    result = _handle_edit({"input": "x", "mode": "bogus"})
    data = json.loads(result)
    assert "error" in data
    assert "bogus" in data["error"]


# ---------------------------------------------------------------------------
# T15 review fixes: MV moves, replace contract, local-backend guard
# ---------------------------------------------------------------------------


def test_hashline_mv_moves_source_to_dest(monkeypatch, tmp_path):
    """A hashline MV must land the destination AND unlink the source — the
    write loop may not silently copy (source left behind)."""
    monkeypatch.delenv("XAVANI_EDIT_MODE", raising=False)
    monkeypatch.setattr(edit_tool, "get_config_path", lambda: tmp_path / "no-such-config.yaml")

    src = tmp_path / "old.py"
    src.write_text("a\nb\nc\n", encoding="utf-8")
    dest = tmp_path / "new.py"
    default_store.record(str(src), "a\nb\nc\n", ranges=((1, 3),))
    tag = default_store.get(str(src)).tag

    payload = f"[{src}#{tag}]\nPUT 1.=1:\n+A1\nMV {dest}\n"
    result = _handle_edit({"input": payload, "mode": "hashline"}, task_id="t-mv")
    data = json.loads(result)
    assert data.get("ok") is True, data
    assert dest.read_text(encoding="utf-8") == "A1\nb\nc\n"
    assert not src.exists()


def test_hashline_mv_refuses_sensitive_dest(monkeypatch, tmp_path):
    """MV destination must pass the sensitive-path guard; on rejection the
    source must be left untouched (no partial move)."""
    monkeypatch.delenv("XAVANI_EDIT_MODE", raising=False)
    monkeypatch.setattr(edit_tool, "get_config_path", lambda: tmp_path / "no-such-config.yaml")

    src = tmp_path / "old.py"
    src.write_text("a\nb\nc\n", encoding="utf-8")
    dest = tmp_path / "new.py"
    default_store.record(str(src), "a\nb\nc\n", ranges=((1, 3),))
    tag = default_store.get(str(src)).tag

    monkeypatch.setattr(
        file_tools,
        "_SENSITIVE_PATH_PREFIXES",
        file_tools._SENSITIVE_PATH_PREFIXES + (str(tmp_path) + os.sep,),
    )
    payload = f"[{src}#{tag}]\nMV {dest}\n"
    result = _handle_edit({"input": payload, "mode": "hashline"}, task_id="t-mv-sens")
    data = json.loads(result)
    assert "error" in data
    assert "sensitive" in data["error"].lower()
    assert src.read_text(encoding="utf-8") == "a\nb\nc\n"
    assert not dest.exists()


def test_hashline_auto_records_unseen_file_before_apply(monkeypatch, tmp_path):
    """Auto-record success path: a hashline edit on a file that was never
    read (no recorded snapshot) must auto-record from disk and apply."""
    monkeypatch.delenv("XAVANI_EDIT_MODE", raising=False)
    monkeypatch.setattr(edit_tool, "get_config_path", lambda: tmp_path / "no-such-config.yaml")

    f = tmp_path / "fresh.py"
    f.write_text("a\nb\nc\n", encoding="utf-8")
    assert default_store.get(str(f)) is None
    tag = compute_tag("a\nb\nc\n")

    payload = f"[{f}#{tag}]\nPUT 2.=2:\n+X\n"
    result = _handle_edit({"input": payload, "mode": "hashline"}, task_id="t-auto")
    data = json.loads(result)
    assert data.get("ok") is True, data
    assert f.read_text(encoding="utf-8") == "a\nX\nc\n"


def test_replace_mode_unique_required_when_multiple_occurrences(tmp_path):
    """count>1 without replace_all must error (nothing written)."""
    f = tmp_path / "note.txt"
    f.write_text("x y x\n", encoding="utf-8")
    result = _handle_edit(
        {"mode": "replace", "path": str(f), "old_string": "x", "new_string": "z"},
        task_id="t-uniq",
    )
    data = json.loads(result)
    assert "error" in data
    assert "replace_all" in data["error"]
    assert f.read_text(encoding="utf-8") == "x y x\n"


def test_replace_mode_replace_all_replaces_every_occurrence(tmp_path):
    f = tmp_path / "note.txt"
    f.write_text("x y x\n", encoding="utf-8")
    result = _handle_edit(
        {
            "mode": "replace",
            "path": str(f),
            "old_string": "x",
            "new_string": "z",
            "replace_all": True,
        },
        task_id="t-all",
    )
    data = json.loads(result)
    assert data.get("ok") is True, data
    assert data["replaced"] == 2
    assert f.read_text(encoding="utf-8") == "z y z\n"


def test_replace_mode_rejects_non_string_new_string(tmp_path):
    """new_string must be a str; a dict must produce a tool error, never a
    TypeError escaping the tool via str.replace()."""
    f = tmp_path / "note.txt"
    f.write_text("hello world\n", encoding="utf-8")
    result = _handle_edit(
        {"mode": "replace", "path": str(f), "old_string": "world", "new_string": {"x": 1}},
        task_id="t-typ",
    )
    data = json.loads(result)
    assert "error" in data
    assert "new_string" in data["error"]
    assert f.read_text(encoding="utf-8") == "hello world\n"


def test_hashline_mode_refuses_nonlocal_backend(monkeypatch, tmp_path):
    """hashline writes directly on the local filesystem; with a non-local
    terminal backend active it must refuse instead of editing the wrong file."""
    monkeypatch.setenv("TERMINAL_ENV", "docker")
    result = _handle_edit(
        {"input": "[x.py#ABCD]\nPUT 1.=1:\n+A\n", "mode": "hashline"},
        task_id="t-be",
    )
    data = json.loads(result)
    assert "error" in data
    assert "local" in data["error"].lower()


def test_replace_mode_refuses_nonlocal_backend(monkeypatch, tmp_path):
    monkeypatch.setenv("TERMINAL_ENV", "docker")
    f = tmp_path / "note.txt"
    f.write_text("hello\n", encoding="utf-8")
    result = _handle_edit(
        {"mode": "replace", "path": str(f), "old_string": "hello", "new_string": "bye"},
        task_id="t-be2",
    )
    data = json.loads(result)
    assert "error" in data
    assert "local" in data["error"].lower()
    assert f.read_text(encoding="utf-8") == "hello\n"
