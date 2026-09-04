import importlib


def test_sizefmt_imports():
    mod = importlib.import_module("xavani_cli.sizefmt")
    assert mod is not None


def test_format_bytes_static():
    mod = importlib.import_module("xavani_cli.sizefmt")
    assert mod.format_bytes(2048) == "2.0 KB"
    assert mod.format_bytes(None) == "?"
