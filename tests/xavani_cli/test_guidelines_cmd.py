# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for xavani_cli/guidelines_cmd.py — CLI subcommand."""

import pytest

from xavani_cli import guidelines_cmd as gc
from xavani_cli.research_guidelines import list_guideline_names

pytestmark = pytest.mark.unit


class TestGuidelinesCmd:
    """Test the guidelines CLI command."""

    def test_build_parser(self):
        """Parser builds without error."""
        parser = gc.build_parser()
        assert parser is not None

    def test_cmd_list_prints_21_names(self, capsys):
        """_cmd_list prints all 21 guideline names."""
        exit_code = gc._cmd_list()
        assert exit_code == 0
        output = capsys.readouterr().out
        names = list_guideline_names()
        for name in names:
            assert name in output, f"Missing {name} in list output"

    def test_cmd_show_hickey(self, capsys):
        """_cmd_show prints the hickey guideline body."""
        exit_code = gc._cmd_show("hickey-guidelines")
        assert exit_code == 0
        output = capsys.readouterr().out
        assert "Hickey" in output
        assert "Simple Made Easy" in output

    def test_cmd_show_nonexistent(self, capsys):
        """_cmd_show returns non-zero for unknown guideline."""
        exit_code = gc._cmd_show("does-not-exist")
        assert exit_code != 0
        output = capsys.readouterr().out
        assert "not found" in output.lower() or "not found" in capsys.readouterr().err.lower()

    def test_run_slash_list(self):
        """run_slash('list') returns a formatted string with all names."""
        output = gc.run_slash("list")
        assert isinstance(output, str)
        assert len(output) > 100
        names = list_guideline_names()
        for name in names:
            assert name in output

    def test_run_slash_show(self):
        """run_slash('show karpathy-guidelines') returns the body."""
        output = gc.run_slash("show karpathy-guidelines")
        assert "Karpathy" in output
