# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Regression tests for the XavaniCLI OAG process_command override.

The override previously misread the full command line as the command name
and called ``super().process_command(cmd_name, args)`` with two args — the
base contract takes one, so EVERY slash command crashed with
``TypeError: XavaniCLI.process_command() takes 2 positional arguments
but 3 were given`` (seen live when steering in the CLI).
"""

from __future__ import annotations

import inspect
from unittest.mock import patch

import xavani
import pytest

pytestmark = pytest.mark.unit


class TestSplitOagCommand:
    def test_plain_text_returns_empty(self):
        assert xavani._split_oag_command("hello world") == ("", "")

    def test_slash_with_args(self):
        assert xavani._split_oag_command("/install my-server") == ("install", "my-server")

    def test_slash_without_args(self):
        assert xavani._split_oag_command("/gateway-up") == ("gateway-up", "")

    def test_case_insensitive_name(self):
        assert xavani._split_oag_command("/INSTALL foo") == ("install", "foo")


class TestDispatchOagCommand:
    def test_registered_handler_runs_with_args_and_cli(self):
        seen: list[tuple[str, object]] = []

        def handler(args: str, cli=None) -> str:
            seen.append((args, cli))
            return "ok"

        with patch.object(xavani, "OAG_COMMAND_HANDLERS", {"install": handler}):
            result = xavani.dispatch_oag_command("/install my-server", cli="CLI")
        assert result is True
        assert seen == [("my-server", "CLI")]

    def test_unknown_command_returns_none(self):
        with patch.object(xavani, "OAG_COMMAND_HANDLERS", {}):
            assert xavani.dispatch_oag_command("/status", cli=None) is None

    def test_plain_text_returns_none(self):
        with patch.object(xavani, "OAG_COMMAND_HANDLERS", {"install": lambda *a, **k: "x"}):
            assert xavani.dispatch_oag_command("hello", cli=None) is None


class TestProcessCommandSignature:
    """The core regression guard: the override must keep the parent contract."""

    def test_override_takes_single_command_argument(self):
        sig = inspect.signature(xavani.XavaniCLI.process_command)
        params = list(sig.parameters)
        assert params == ["self", "command"], (
            "process_command must accept exactly (self, command) — the old "
            "(cmd_name, args) signature crashed every slash command"
        )

    def test_override_calls_super_with_single_argument(self):
        """Verifies the override source passes one argument to super()."""
        import inspect as _inspect

        src = _inspect.getsource(xavani.XavaniCLI.process_command)
        assert "super().process_command(command)" in src, (
            "the override must forward the untouched command line to the parent"
        )
        assert "super().process_command(cmd_name" not in src
