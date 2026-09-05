from __future__ import annotations


def test_web_deps_import_succeeds():
    import xavani_cli.web_deps as web_deps

    assert web_deps is not None


def test_web_deps_late_proxy_resolves_known_web_server_name():
    from xavani_cli.web_deps import late_attr

    assert late_attr("_SESSION_TOKEN") is not None
