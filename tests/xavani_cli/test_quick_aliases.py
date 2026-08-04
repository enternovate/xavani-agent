# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""C10: quick-session aliases tests.

Common commands expose short CLI-only shortcuts (cli_aliases). They
resolve like aliases in the CLI but never consume platform slash slots
(Slack's hard 50-command cap stays stable).
"""

from xavani_cli.commands import COMMANDS, resolve_command, slack_native_slashes


def _name(alias: str) -> str:
    resolved = resolve_command(alias)
    assert resolved is not None
    return resolved.name


def test_resolve_alias_to_command():
    assert _name("cm") == "compress"
    assert _name("r") == "resume"
    assert _name("ls") == "sessions"
    assert _name("st") == "status"
    assert _name("g") == "goal"
    assert _name("who") == "profile"


def test_resolve_with_leading_slash():
    assert _name("/cm") == "compress"
    assert _name("/g") == "goal"
    assert _name("/r") == "resume"


def test_resolve_original_names_still_work():
    assert _name("compress") == "compress"
    assert _name("resume") == "resume"
    assert _name("sessions") == "sessions"


def test_aliases_appear_in_commands_dict():
    assert "/cm" in COMMANDS
    assert "/r" in COMMANDS
    assert "/ls" in COMMANDS
    assert "/st" in COMMANDS
    assert "/g" in COMMANDS
    assert "/who" in COMMANDS


def test_alias_points_to_canonical():
    assert "CLI shortcut for /compress" in COMMANDS["/cm"]
    assert "CLI shortcut for /goal" in COMMANDS["/g"]


def test_unknown_command_returns_none():
    assert resolve_command("definitely-not-a-command") is None


def test_existing_aliases_preserved():
    assert _name("bg") == "background"
    assert _name("reset") == "new"
    assert _name("fork") == "branch"


def test_cli_aliases_not_in_slack_slashes():
    """CLI shortcuts must not consume Slack's 50-slot budget."""
    names = {n for n, _d, _h in slack_native_slashes()}
    assert "cm" not in names
    assert "r" not in names
    assert "ls" not in names
    assert "st" not in names
    assert "g" not in names
    assert "who" not in names
    # The legacy short aliases still fit.
    assert "q" in names
    assert "bg" in names
    assert "btw" in names
    assert "reset" in names
