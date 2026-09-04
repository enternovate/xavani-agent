import importlib


def test_model_selection_guards_imports():
    mod = importlib.import_module("xavani_cli.model_selection_guards")
    assert mod is not None


def test_model_selection_guards_main_entry():
    mod = importlib.import_module("xavani_cli.model_selection_guards")
    assert callable(mod.selection_warnings)
