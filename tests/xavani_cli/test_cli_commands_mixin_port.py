from xavani_cli import cli_commands_mixin


def test_import_succeeds():
    assert cli_commands_mixin is not None


def test_mixin_is_class():
    assert isinstance(cli_commands_mixin.CLICommandsMixin, type)


def test_emit_focus_recovery_line_resets_counter():
    obj = cli_commands_mixin.CLICommandsMixin.__new__(cli_commands_mixin.CLICommandsMixin)
    obj._focus_hidden_lines = 5
    obj._focus_last_counted_tool = "bash"
    obj._focus_view_enabled = False
    obj._emit_focus_recovery_line()
    assert obj._focus_hidden_lines == 0
    assert obj._focus_last_counted_tool is None
