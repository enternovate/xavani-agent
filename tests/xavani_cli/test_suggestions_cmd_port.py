import importlib


def test_suggestions_cmd_imports():
    mod = importlib.import_module("xavani_cli.suggestions_cmd")
    assert mod is not None


def test_fmt_pending_empty_static():
    mod = importlib.import_module("xavani_cli.suggestions_cmd")
    text = mod._fmt_pending([])
    assert "No suggested automations" in text
