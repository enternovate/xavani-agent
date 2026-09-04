def test_credential_lifecycle_import_succeeds():
    import xavani_cli.credential_lifecycle as cl

    assert cl is not None


def test_providers_for_unknown_env_var_returns_empty():
    from xavani_cli.credential_lifecycle import _providers_for_env_var

    assert _providers_for_env_var("XAVANI_DEFINITELY_NOT_A_VAR_12345") == []


def test_scrub_config_yaml_mirrors_empty_old_value_returns_empty():
    from xavani_cli.credential_lifecycle import _scrub_config_yaml_mirrors

    assert _scrub_config_yaml_mirrors("", "new-value") == []
    assert _scrub_config_yaml_mirrors("", None) == []
