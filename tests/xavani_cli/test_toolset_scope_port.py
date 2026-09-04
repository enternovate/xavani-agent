import importlib


def test_toolset_scope_imports():
    mod = importlib.import_module("xavani_cli.toolset_scope")
    assert mod is not None


def test_toolset_allowed_for_platform_static():
    mod = importlib.import_module("xavani_cli.toolset_scope")
    assert mod.toolset_allowed_for_platform("discord", "discord") is True
    assert mod.toolset_allowed_for_platform("discord", "cli") is False
