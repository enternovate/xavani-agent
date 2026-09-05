def test_install_identity_import_succeeds():
    import xavani_cli.install_identity  # noqa: F401


def test_install_identity_exposes_get_install_id():
    from xavani_cli.install_identity import get_install_id

    assert callable(get_install_id)
