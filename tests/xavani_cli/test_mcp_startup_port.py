def test_mcp_startup_import_succeeds():
    import xavani_cli.mcp_startup  # noqa: F401


def test_mcp_startup_exposes_set_mcp_server_filter():
    from xavani_cli.mcp_startup import set_mcp_server_filter

    assert callable(set_mcp_server_filter)
