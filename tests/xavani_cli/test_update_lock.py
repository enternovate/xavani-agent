# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the cross-process update lock (C06).

The lock keeps two ``xavani update`` runs from mutating the same repo
at the same time.  These tests exercise the lock helpers in isolation;
no git or pip command ever runs.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from xavani_cli.main import (
    _acquire_update_lock,
    _release_update_lock,
    _update_lock_path,
)


@pytest.fixture
def locked_home(tmp_path: Path, monkeypatch) -> Path:
    """Point XAVANI_HOME at a temp dir for the duration of the test."""
    monkeypatch.setenv("XAVANI_HOME", str(tmp_path))
    return tmp_path


def test_update_lock_path_under_home(locked_home: Path) -> None:
    """The lock file must live inside the Xavani home directory."""
    assert _update_lock_path() == locked_home / ".update.lock"


def test_acquire_then_release_roundtrip(locked_home: Path) -> None:
    """A released lock must be acquirable again."""
    handle = _acquire_update_lock()
    assert handle is not None
    _release_update_lock(handle)
    handle2 = _acquire_update_lock()
    assert handle2 is not None
    _release_update_lock(handle2)


def test_second_acquire_fails_while_held(locked_home: Path) -> None:
    """A held lock must refuse a second concurrent update."""
    handle = _acquire_update_lock()
    assert handle is not None
    try:
        assert _acquire_update_lock() is None
    finally:
        _release_update_lock(handle)
    assert _acquire_update_lock() is not None


def test_release_none_is_safe(locked_home: Path) -> None:
    """Releasing a missing handle must not raise."""
    _release_update_lock(None)
