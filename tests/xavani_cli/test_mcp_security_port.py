import importlib


def test_mcp_security_imports():
    mod = importlib.import_module("xavani_cli.mcp_security")
    assert mod is not None


def test_mcp_security_main_entry():
    mod = importlib.import_module("xavani_cli.mcp_security")
    assert callable(mod.validate_mcp_server_entry)
