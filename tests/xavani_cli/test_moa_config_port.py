def test_moa_config_imports():
    import xavani_cli.moa_config as moa_config

    assert moa_config is not None


def test_default_moa_preset_name_is_default():
    from xavani_cli.moa_config import DEFAULT_MOA_PRESET_NAME

    assert DEFAULT_MOA_PRESET_NAME == "default"
