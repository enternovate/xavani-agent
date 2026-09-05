import importlib


def test_skin_cmd_imports():
    mod = importlib.import_module("xavani_cli.skin_cmd")
    assert mod is not None


def test_hex_pattern_static():
    mod = importlib.import_module("xavani_cli.skin_cmd")
    assert mod._HEX_RE.match("#ff6600") is not None
    assert mod._HEX_RE.match("#FF6600") is not None
    assert mod._HEX_RE.match("red") is None
    assert mod._HEX_RE.match("#12345") is None
