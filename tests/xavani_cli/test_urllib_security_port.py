import importlib


def test_urllib_security_imports():
    mod = importlib.import_module("xavani_cli.urllib_security")
    assert mod is not None


def test_url_origin_static():
    mod = importlib.import_module("xavani_cli.urllib_security")
    assert mod.url_origin("https://example.com:443/x") == ("https", "example.com", 443)
    assert mod.url_origin("http://example.com/y")[2] == 80
