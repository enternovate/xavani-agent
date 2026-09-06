import importlib


def test_update_cmd_imports():
    mod = importlib.import_module("xavani_cli.update_cmd")
    assert mod is not None


def test_update_cmd_exposes_update_entry():
    mod = importlib.import_module("xavani_cli.update_cmd")
    assert callable(getattr(mod, "_cmd_update_impl", None))


def test_update_cmd_pure_helper_static_inputs():
    mod = importlib.import_module("xavani_cli.update_cmd")
    assert mod._is_fork(None) is False
    assert mod._is_fork("https://github.com/Enternovate/xavani-agent.git") is False
    assert mod._is_fork("https://github.com/someone/my-fork.git") is True
