# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""C07 — bang shell (`!cmd`) tests."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch


def _import_cli():
    import cli as cli_mod

    return cli_mod


class TestBangShell(unittest.TestCase):
    def _stub(self):
        return SimpleNamespace()

    def test_empty_command_shows_usage(self):
        cli_mod = _import_cli()
        with patch.object(cli_mod, "_cprint") as mock_cprint:
            cli_mod.XavaniCLI._execute_bang_shell(self._stub(), "   ")
        printed = " ".join(str(c) for c in mock_cprint.call_args_list)
        self.assertIn("Usage: !<shell command>", printed)

    def test_echo_output_is_printed(self):
        cli_mod = _import_cli()
        with patch.object(cli_mod, "_cprint") as mock_cprint:
            cli_mod.XavaniCLI._execute_bang_shell(self._stub(), "echo bang-shell-ok")
        printed = " ".join(str(c) for c in mock_cprint.call_args_list)
        self.assertIn("bang-shell-ok", printed)

    def test_nonzero_exit_is_surfaced(self):
        cli_mod = _import_cli()
        with patch.object(cli_mod, "_cprint") as mock_cprint:
            cli_mod.XavaniCLI._execute_bang_shell(self._stub(), "exit 3")
        printed = " ".join(str(c) for c in mock_cprint.call_args_list)
        self.assertIn("exit code 3", printed)

    def test_stderr_is_printed(self):
        cli_mod = _import_cli()
        with patch.object(cli_mod, "_cprint") as mock_cprint:
            cli_mod.XavaniCLI._execute_bang_shell(self._stub(), "echo oops 1>&2")
        printed = " ".join(str(c) for c in mock_cprint.call_args_list)
        self.assertIn("oops", printed)


if __name__ == "__main__":
    unittest.main()
