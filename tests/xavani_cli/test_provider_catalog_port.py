import importlib


def test_provider_catalog_imports():
    mod = importlib.import_module("xavani_cli.provider_catalog")
    assert mod is not None


def test_provider_catalog_main_entry_exposed():
    mod = importlib.import_module("xavani_cli.provider_catalog")
    assert callable(getattr(mod, "provider_catalog", None))
