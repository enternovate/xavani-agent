import importlib


def test_install_repair_imports():
    mod = importlib.import_module("xavani_cli._install_repair")
    assert mod is not None


def test_run_core_install_callable():
    mod = importlib.import_module("xavani_cli._install_repair")
    assert callable(mod.run_core_install)


def test_install_repair_has_no_hermes_brand_leftovers():
    from pathlib import Path
    module_path = Path(__file__).resolve().parents[2] / "xavani_cli" / "_install_repair.py"
    text = module_path.read_text(encoding="utf-8")
    assert "hermes" not in text.lower()
