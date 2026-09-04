from tools.approval import (
    _command_matches_permanent_allowlist,
    _has_allowlist_shell_operator,
)


def test_has_allowlist_shell_operator_pipe():
    assert _has_allowlist_shell_operator("ls | grep foo") is True


def test_has_allowlist_shell_operator_simple():
    assert _has_allowlist_shell_operator("ls -la") is False


def test_command_matches_permanent_allowlist_unknown():
    assert _command_matches_permanent_allowlist("some-unknown-cmd-xyz") is False
