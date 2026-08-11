# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the first-run setup wizard auto-launch (backlog F138).

A fresh install (no provider configured) routes the bare ``xavani``
invocation into the existing setup wizard. Configured installs and
non-interactive environments skip it entirely.
"""

from unittest.mock import patch

from xavani_cli import main as main_mod


def test_first_run_routes_into_wizard_when_unconfigured_and_tty():
    with patch.object(main_mod, "_has_any_provider_configured", return_value=False), patch(
        "xavani_cli.setup.is_interactive_stdin", return_value=True
    ), patch("xavani_cli.setup.run_setup_wizard") as wizard:
        ran = main_mod._maybe_first_run_setup()

    assert ran is True
    wizard.assert_called_once_with(None)


def test_configured_install_skips_wizard():
    with patch.object(main_mod, "_has_any_provider_configured", return_value=True), patch(
        "xavani_cli.setup.run_setup_wizard"
    ) as wizard:
        ran = main_mod._maybe_first_run_setup()

    assert ran is False
    wizard.assert_not_called()


def test_non_interactive_stdin_skips_wizard():
    with patch.object(main_mod, "_has_any_provider_configured", return_value=False), patch(
        "xavani_cli.setup.is_interactive_stdin", return_value=False
    ), patch("xavani_cli.setup.run_setup_wizard") as wizard:
        ran = main_mod._maybe_first_run_setup()

    assert ran is False
    wizard.assert_not_called()
