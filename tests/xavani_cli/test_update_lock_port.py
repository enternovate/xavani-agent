from __future__ import annotations

from pathlib import Path


def test_update_lock_import_succeeds():
    import xavani_cli.update_lock as update_lock

    assert callable(update_lock.update_marker_path)


def test_update_marker_path_returns_path():
    from xavani_cli.update_lock import update_marker_path

    assert isinstance(update_marker_path(), Path)


def test_get_process_xavani_home_returns_path():
    from xavani_constants import get_process_xavani_home

    assert isinstance(get_process_xavani_home(), Path)
