def test_has_enabled_agent_plugin_mcp_empty_dict_returns_false():
    from xavani_cli.agent_plugins import has_enabled_agent_plugin_mcp

    assert has_enabled_agent_plugin_mcp({}) is False


def test_has_enabled_portable_mcp_safe_mode_returns_false(monkeypatch):
    from xavani_cli.plugins import PluginManager

    monkeypatch.setenv("XAVANI_SAFE_MODE", "1")
    manager = PluginManager()
    assert manager.has_enabled_portable_mcp({"plugins": {"enabled": ["anything"]}}) is False


def test_agent_plugins_wrapper_calls_through(monkeypatch):
    import xavani_cli.agent_plugins as agent_plugins_mod
    import xavani_cli.plugins as plugins_mod

    seen = {}

    def _fake(raw_config):
        seen["config"] = raw_config
        return True

    monkeypatch.setattr(plugins_mod, "has_enabled_agent_plugin_mcp", _fake)
    config = {"plugins": {"enabled": ["x"]}}
    assert agent_plugins_mod.has_enabled_agent_plugin_mcp(config) is True
    assert seen["config"] is config
