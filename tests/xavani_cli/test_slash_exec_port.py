def test_slash_exec_imports():
    import xavani_cli.slash_exec as mod

    assert mod is not None


def test_resolve_executor_none_for_unmigrated():
    from types import SimpleNamespace

    from xavani_cli.slash_exec import resolve_executor

    assert resolve_executor(SimpleNamespace()) is None
    assert resolve_executor(SimpleNamespace(execute="nope")) is None


def test_command_context_defaults():
    from xavani_cli.slash_exec import CommandContext

    ctx = CommandContext()
    assert ctx.surface == "cli"
    assert ctx.args == ""
