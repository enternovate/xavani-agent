import importlib


def test_session_listing_imports():
    mod = importlib.import_module("xavani_cli.session_listing")
    assert mod is not None


def test_parse_and_format_static():
    mod = importlib.import_module("xavani_cli.session_listing")
    assert mod.parse_session_listing_args("list") == (False, False, "", None)
    include_all, include_unnamed, target, query = mod.parse_session_listing_args("all search deploy")
    assert (include_all, query) == (True, "deploy")
    assert target == ""
    assert include_unnamed is False
    rows = [{"id": "s1", "title": "Deploy", "preview": "did a deploy", "source": "cli"}]
    out = mod.format_gateway_session_listing(rows)
    assert "Deploy" in out
    assert "s1" in out
