import importlib


def test_terminal_breadcrumbs_imports():
    mod = importlib.import_module("xavani_cli.terminal_breadcrumbs")
    assert mod is not None


def test_sanitize_static():
    mod = importlib.import_module("xavani_cli.terminal_breadcrumbs")
    assert mod._sanitize("/dev/pts/3") == "dev-pts-3"
