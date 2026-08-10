# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for S3-8 fuzzy slash-command matching (backlog F147)."""
from unittest.mock import MagicMock, patch

from cli import XavaniCLI


def _make_cli():
    cli_obj = XavaniCLI.__new__(XavaniCLI)
    cli_obj.config = {}
    cli_obj.console = MagicMock()
    cli_obj.agent = None
    cli_obj.conversation_history = []
    cli_obj.session_id = None
    cli_obj._pending_input = MagicMock()
    cli_obj._app = None
    return cli_obj


def _printed(mock_cprint):
    return " ".join(str(c) for c in mock_cprint.call_args_list)


class TestFuzzySlashSuggestion:
    def test_typo_suggests_but_does_not_run_without_confirmation(self):
        """/compct should print 'Did you mean /compact?' and NOT run /compact."""
        cli_obj = _make_cli()
        with patch("cli._cprint") as mock_cprint, \
             patch.object(cli_obj, "_manual_compress") as mock_run, \
             patch.object(cli_obj, "_prompt_text_input", return_value=None) as mock_ask:
            cli_obj.process_command("/compct")
        printed = _printed(mock_cprint)
        assert "Did you mean /compact?" in printed
        mock_run.assert_not_called()
        mock_ask.assert_called_once()

    def test_confirming_runs_target_command(self):
        """/compct + 'y' should dispatch /compact (mock the target handler)."""
        cli_obj = _make_cli()
        with patch.object(cli_obj, "_manual_compress") as mock_run, \
             patch.object(cli_obj, "_prompt_text_input", return_value="y"):
            cli_obj.process_command("/compct")
        mock_run.assert_called_once_with("/compact")

    def test_declining_keeps_unknown_command_behavior(self):
        """/compct + 'n' should keep the existing unknown-command error."""
        cli_obj = _make_cli()
        with patch("cli._cprint") as mock_cprint, \
             patch.object(cli_obj, "_manual_compress") as mock_run, \
             patch.object(cli_obj, "_prompt_text_input", return_value="n"):
            cli_obj.process_command("/compct")
        printed = _printed(mock_cprint)
        assert "Unknown command" in printed
        mock_run.assert_not_called()

    def test_far_input_gets_no_suggestion(self):
        """/zzzqqq is far from every command — no suggestion, no prompt."""
        cli_obj = _make_cli()
        with patch("cli._cprint") as mock_cprint, \
             patch.object(cli_obj, "_prompt_text_input") as mock_ask:
            cli_obj.process_command("/zzzqqq")
        printed = _printed(mock_cprint)
        assert "Did you mean" not in printed
        assert "Unknown command" in printed
        mock_ask.assert_not_called()

    def test_exact_match_path_untouched(self):
        """/help exact match dispatches normally with no suggestion."""
        cli_obj = _make_cli()
        with patch.object(cli_obj, "show_help") as mock_help, \
             patch("cli._cprint") as mock_cprint, \
             patch.object(cli_obj, "_prompt_text_input") as mock_ask:
            cli_obj.process_command("/help")
        mock_help.assert_called_once()
        assert "Did you mean" not in _printed(mock_cprint)
        mock_ask.assert_not_called()
