from xavani_cli.relay_plugin_cutover import (
    RELAY_PLUGINS_CONFIG_ENV,
    configured_legacy_relay_env_vars,
    legacy_relay_plugin_keys,
)


def test_import_succeeds():
    assert legacy_relay_plugin_keys is not None
    assert configured_legacy_relay_env_vars is not None


def test_config_env_uses_xavani_prefix():
    assert RELAY_PLUGINS_CONFIG_ENV == "XAVANI_NEMO_RELAY_PLUGINS_TOML"
    assert legacy_relay_plugin_keys("notalist") == ()
