import importlib


def test_focus_view_imports():
    mod = importlib.import_module("xavani_cli.focus_view")
    assert mod is not None


def test_normalize_tool_progress_mode_off():
    mod = importlib.import_module("xavani_cli.focus_view")
    assert mod.normalize_tool_progress_mode(False) == "off"
    assert mod.normalize_tool_progress_mode("verbose") == "verbose"


def test_resolve_focus_arg_on_off():
    mod = importlib.import_module("xavani_cli.focus_view")
    assert mod.resolve_focus_arg("on", False) == ("set", True)
    assert mod.resolve_focus_arg("off", True) == ("set", False)
