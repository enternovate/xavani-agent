def test_process_identity_import_succeeds():
    import xavani_cli.process_identity  # noqa: F401


def test_install_id_returns_nonempty_string():
    from xavani_cli.process_identity import install_id

    result = install_id()
    assert isinstance(result, str)
    assert result != ""


def test_spawn_tag_is_class():
    from xavani_cli.process_identity import SpawnTag

    assert isinstance(SpawnTag, type)
