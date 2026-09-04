def test_agent_plugins_import_succeeds():
    import xavani_cli.agent_plugins  # noqa: F401


def test_agent_plugin_error_is_exception_class():
    from xavani_cli.agent_plugins import AgentPluginError

    assert issubclass(AgentPluginError, Exception)


def test_has_enabled_agent_plugin_mcp_empty_dict_returns_false():
    from xavani_cli.agent_plugins import has_enabled_agent_plugin_mcp

    assert has_enabled_agent_plugin_mcp({}) is False
