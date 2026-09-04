import importlib


def test_middleware_imports():
    mod = importlib.import_module("xavani_cli.middleware")
    assert mod is not None


def test_middleware_plugin_wrappers_import():
    from xavani_cli.plugins import has_middleware, invoke_middleware

    assert callable(invoke_middleware)
    assert callable(has_middleware)


def test_has_middleware_unknown_kind_false():
    from xavani_cli.plugins import has_middleware

    assert has_middleware("no_such_middleware_kind_xyz") is False
