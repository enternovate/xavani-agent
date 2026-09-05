import importlib


def test_partial_compress_imports():
    mod = importlib.import_module("xavani_cli.partial_compress")
    assert mod is not None


def test_partial_compress_main_entry_exposed():
    mod = importlib.import_module("xavani_cli.partial_compress")
    assert callable(getattr(mod, "split_history_for_partial_compress", None))
