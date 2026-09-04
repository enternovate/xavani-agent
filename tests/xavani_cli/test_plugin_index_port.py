import importlib


def test_plugin_index_imports():
    mod = importlib.import_module("xavani_cli.plugin_index")
    assert mod is not None


def test_plugin_index_exposes_main_entry():
    mod = importlib.import_module("xavani_cli.plugin_index")
    assert callable(getattr(mod, "load_index", None))


def test_load_config_readonly_returns_dict():
    from xavani_cli.config import load_config_readonly

    assert isinstance(load_config_readonly(), dict)
