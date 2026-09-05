def test_memory_oauth_import_succeeds():
    import xavani_cli.memory_oauth  # noqa: F401


def test_memory_oauth_exposes_router():
    from xavani_cli.memory_oauth import router

    assert router is not None
