def test_lifecycle_import_succeeds():
    import xavani_cli.lifecycle  # noqa: F401


def test_lifecycle_exposes_invoke_hook():
    from xavani_cli.lifecycle import invoke_hook

    assert callable(invoke_hook)
