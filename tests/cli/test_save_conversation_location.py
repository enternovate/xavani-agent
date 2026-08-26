# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for /save — the conversation snapshot slash command.

Regression: the old implementation wrote ``xavani_conversation_<ts>.json``
to the current working directory (CWD). Users who ran /save expected the
file to be discoverable via ``xavani sessions browse``, but CWD-resident
snapshots are not indexed in the state DB and are generally invisible.
The fix writes snapshots under ``~/.xavani/sessions/saved/`` and prints
the absolute path plus the resume hint for the live session.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def xavani_home(tmp_path, monkeypatch):
    home = tmp_path / ".xavani"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("XAVANI_HOME", str(home))
    # Clear any cached xavani_home computation
    import xavani_constants
    if hasattr(xavani_constants, "_xavani_home_cache"):
        xavani_constants._xavani_home_cache = None
    return home


def _make_stub_cli(history):
    """Build a minimal object exposing just what save_conversation uses."""
    return SimpleNamespace(
        conversation_history=history,
        model="test-model",
        session_id="20260101_120000_abc123",
        session_start=datetime(2026, 1, 1, 12, 0, 0),
    )


@contextmanager
def _fresh_cli_module():
    original_modules = {
        name: module
        for name, module in sys.modules.items()
        if name.startswith("cli") or name == "xavani_constants"
    }
    try:
        for name in original_modules:
            sys.modules.pop(name, None)
        yield importlib.import_module("cli")
    finally:
        for name in [
            name
            for name in sys.modules
            if name.startswith("cli") or name == "xavani_constants"
        ]:
            sys.modules.pop(name, None)
        sys.modules.update(original_modules)


def test_save_conversation_reload_restores_cached_cli_module(xavani_home):
    """A fresh /save import must not leave fuzzy tests with stale cli globals."""
    import cli as original_cli

    with _fresh_cli_module() as reloaded_cli:
        assert reloaded_cli is not original_cli
        reloaded_cli.XavaniCLI.save_conversation(
            _make_stub_cli([{"role": "user", "content": "hi"}])
        )
    assert sys.modules["cli"] is original_cli
    assert original_cli.XavaniCLI.process_command.__globals__ is vars(original_cli)


def test_save_conversation_writes_under_xavani_home(xavani_home, tmp_path, monkeypatch, capsys):
    """Snapshot must land under ~/.xavani/sessions/saved/, not CWD."""
    # Change CWD to a different directory to prove the file does NOT go there.
    work = tmp_path / "somewhere-else"
    work.mkdir()
    monkeypatch.chdir(work)

    stub = _make_stub_cli([
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ])

    with _fresh_cli_module() as cli:
        cli.XavaniCLI.save_conversation(stub)

    # File must NOT be in CWD
    cwd_leak = list(work.glob("xavani_conversation_*.json"))
    assert not cwd_leak, f"snapshot leaked to CWD: {cwd_leak}"

    # File MUST be under ~/.xavani/sessions/saved/
    saved_dir = xavani_home / "sessions" / "saved"
    assert saved_dir.is_dir(), "expected saved/ subdirectory to be created"
    files = list(saved_dir.glob("xavani_conversation_*.json"))
    assert len(files) == 1, files

    payload = json.loads(files[0].read_text())
    assert payload["model"] == "test-model"
    assert payload["session_id"] == "20260101_120000_abc123"
    assert payload["messages"] == [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]

    # User-facing message must include the absolute path AND the resume hint.
    out = capsys.readouterr().out
    assert str(files[0]) in out, out
    assert "xavani --resume 20260101_120000_abc123" in out, out


def test_save_conversation_empty_history_does_nothing(xavani_home, capsys):
    stub = _make_stub_cli([])
    with _fresh_cli_module() as cli:
        cli.XavaniCLI.save_conversation(stub)

    saved_dir = xavani_home / "sessions" / "saved"
    assert not saved_dir.exists() or not list(saved_dir.iterdir())
    out = capsys.readouterr().out
    assert "No conversation to save" in out
