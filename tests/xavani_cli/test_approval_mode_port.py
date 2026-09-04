import importlib


def test_approval_mode_imports():
    mod = importlib.import_module("xavani_cli.approval_mode")
    assert mod is not None


def test_valid_approval_modes():
    mod = importlib.import_module("xavani_cli.approval_mode")
    assert mod.VALID_APPROVAL_MODES == ("manual", "smart", "off")


def test_run_approval_mode_command_none_returns_unchanged():
    mod = importlib.import_module("xavani_cli.approval_mode")
    result = mod.run_approval_mode_command(None)
    assert result.ok is True
    assert result.changed is False
