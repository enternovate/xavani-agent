def test_cli_agent_setup_mixin_import_succeeds():
    import xavani_cli.cli_agent_setup_mixin  # noqa: F401


def test_cli_agent_setup_mixin_is_class():
    from xavani_cli.cli_agent_setup_mixin import CLIAgentSetupMixin

    assert isinstance(CLIAgentSetupMixin, type)


def test_single_query_clarify_callback_no_choices_returns_hint():
    from xavani_cli.cli_agent_setup_mixin import _single_query_clarify_callback

    result = _single_query_clarify_callback("Pick one?")

    assert result == (
        "[single-query mode: no user available to answer 'Pick one?'. Make "
        "the most reasonable assumption you can and continue.]"
    )
