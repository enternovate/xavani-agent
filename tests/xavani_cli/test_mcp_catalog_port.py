def test_mcp_catalog_import_succeeds():
    import xavani_cli.mcp_catalog  # noqa: F401


def test_mcp_catalog_exposes_list_catalog():
    from xavani_cli.mcp_catalog import list_catalog

    assert callable(list_catalog)
