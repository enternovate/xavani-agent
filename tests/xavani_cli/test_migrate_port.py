from __future__ import annotations

from pathlib import Path


def test_migrate_import_succeeds():
    import xavani_cli.migrate as m

    assert m is not None


def test_migrate_commands_callable():
    from xavani_cli.migrate import cmd_migrate, cmd_migrate_xai

    assert callable(cmd_migrate)
    assert callable(cmd_migrate_xai)


def test_resolve_config_path_returns_path():
    from xavani_cli.migrate import _resolve_config_path

    assert isinstance(_resolve_config_path(), Path)
