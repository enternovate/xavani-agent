import importlib


def test_resource_limits_imports():
    mod = importlib.import_module("xavani_cli.resource_limits")
    assert mod is not None


def test_configured_nofile_soft_limit_static():
    mod = importlib.import_module("xavani_cli.resource_limits")
    assert mod.configured_nofile_soft_limit({"runtime": {"nofile_soft_limit": 8192}}) == 8192
    assert mod.configured_nofile_soft_limit({"runtime": {"nofile_soft_limit": 0}}) is None
