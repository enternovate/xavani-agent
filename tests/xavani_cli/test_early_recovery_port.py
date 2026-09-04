import importlib


def test_early_recovery_imports():
    mod = importlib.import_module("xavani_cli._early_recovery")
    assert mod is not None


def test_recover_if_needed_callable():
    mod = importlib.import_module("xavani_cli._early_recovery")
    assert callable(mod.recover_if_needed)
