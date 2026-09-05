import importlib


def test_session_export_imports():
    mod = importlib.import_module("xavani_cli.session_export")
    assert mod is not None


def test_normalize_export_format_static():
    mod = importlib.import_module("xavani_cli.session_export")
    assert mod.normalize_export_format("md") == "markdown"
    assert mod.normalize_export_format("JSONL") == "jsonl"
    assert mod.default_save_filename("abc-123", "md") == "xavani_session_abc-123.md"
