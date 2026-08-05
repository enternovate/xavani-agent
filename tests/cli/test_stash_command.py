# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""C08 — /stash command tests."""

import queue
import unittest
from types import SimpleNamespace
from unittest.mock import patch


def _import_cli():
    import cli as cli_mod

    return cli_mod


class TestStashCommand(unittest.TestCase):
    def setUp(self):
        self._tmp = None

    def _stub(self):
        return SimpleNamespace(_pending_input=queue.Queue())

    def test_save_then_show(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            cli_mod = _import_cli()
            stub = self._stub()
            with (
                patch("xavani_cli.prompt_stash.stash_dir", lambda home=None: tmp),
                patch.object(cli_mod, "_cprint") as mock_cprint,
            ):
                cli_mod.XavaniCLI._handle_stash_command(stub, "/stash draft-one Hello there")
                cli_mod.XavaniCLI._handle_stash_command(stub, "/stash show draft-one")
            printed = " ".join(str(c) for c in mock_cprint.call_args_list)
            self.assertIn("Saved 'draft-one'", printed)
            self.assertIn("Hello there", printed)
            self.assertTrue((tmp / "draft-one.txt").is_file())

    def test_list_and_rm(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            cli_mod = _import_cli()
            stub = self._stub()
            with (
                patch("xavani_cli.prompt_stash.stash_dir", lambda home=None: tmp),
                patch.object(cli_mod, "_cprint") as mock_cprint,
            ):
                cli_mod.XavaniCLI._handle_stash_command(stub, "/stash alpha one")
                cli_mod.XavaniCLI._handle_stash_command(stub, "/stash beta two")
                cli_mod.XavaniCLI._handle_stash_command(stub, "/stash list")
                cli_mod.XavaniCLI._handle_stash_command(stub, "/stash rm alpha")
                cli_mod.XavaniCLI._handle_stash_command(stub, "/stash list")
            printed = " ".join(str(c) for c in mock_cprint.call_args_list)
            self.assertIn("alpha", printed)
            self.assertIn("beta", printed)
            self.assertIn("Removed 'alpha'", printed)
            self.assertFalse((tmp / "alpha.txt").exists())
            self.assertTrue((tmp / "beta.txt").exists())

    def test_load_queues_next_turn(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            cli_mod = _import_cli()
            stub = self._stub()
            with (
                patch("xavani_cli.prompt_stash.stash_dir", lambda home=None: tmp),
                patch.object(cli_mod, "_cprint"),
            ):
                cli_mod.XavaniCLI._handle_stash_command(stub, "/stash q Draft prompt")
                cli_mod.XavaniCLI._handle_stash_command(stub, "/stash load q")
            self.assertEqual(stub._pending_input.get_nowait(), "Draft prompt")

    def test_bad_name_rejected(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            cli_mod = _import_cli()
            with (
                patch("xavani_cli.prompt_stash.stash_dir", lambda home=None: tmp),
                patch.object(cli_mod, "_cprint") as mock_cprint,
            ):
                cli_mod.XavaniCLI._handle_stash_command(self._stub(), "/stash 'bad name!' x")
            printed = " ".join(str(c) for c in mock_cprint.call_args_list)
            self.assertIn("may contain only", printed)


if __name__ == "__main__":
    unittest.main()
