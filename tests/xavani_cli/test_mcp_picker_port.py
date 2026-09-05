def test_mcp_picker_import_succeeds():
    import xavani_cli.mcp_picker  # noqa: F401


def test_mcp_picker_exposes_run_picker():
    from xavani_cli.mcp_picker import run_picker

    assert callable(run_picker)
