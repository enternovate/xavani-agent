import importlib


def test_early_recovery_imports():
    mod = importlib.import_module("xavani_cli._early_recovery")
    assert mod is not None


def test_recover_if_needed_callable():
    mod = importlib.import_module("xavani_cli._early_recovery")
    assert callable(mod.recover_if_needed)


def test_early_recovery_has_no_hermes_brand_leftovers():
    from pathlib import Path
    module_path = Path(__file__).resolve().parents[2] / "xavani_cli" / "_early_recovery.py"
    text = module_path.read_text(encoding="utf-8")
    for token in (".hermes/", "hermes update", "hermes acp", "hermes.exe", "hermes*.exe"):
        assert token not in text
