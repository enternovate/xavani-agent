from __future__ import annotations


def test_plugin_capabilities_import_succeeds():
    import xavani_cli.plugin_capabilities as plugin_capabilities

    assert callable(plugin_capabilities.parse_declared_capabilities)


def test_parse_declared_capabilities_returns_list():
    from xavani_cli.plugin_capabilities import parse_declared_capabilities

    result = parse_declared_capabilities([])

    assert isinstance(result, list)
