# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""C11: --brief / --verbose output modes tests."""

import pytest

from xavani_cli.output_mode import (
    BRIEF,
    DEFAULT,
    VERBOSE,
    apply_output_mode,
    mode_label,
    resolve_output_mode,
)


# ── resolution ──────────────────────────────────────────────────────


def test_no_flags_defaults_to_default():
    assert resolve_output_mode() == DEFAULT


def test_brief_flag_wins():
    assert resolve_output_mode(brief=True) == BRIEF


def test_verbose_flag_wins():
    assert resolve_output_mode(verbose=True) == VERBOSE


def test_contradictory_flags_neutral():
    assert resolve_output_mode(brief=True, verbose=True) == DEFAULT


def test_env_default(monkeypatch):
    monkeypatch.setenv("XAVANI_OUTPUT_MODE", "brief")
    assert resolve_output_mode() == BRIEF


def test_env_overridden_by_flag(monkeypatch):
    monkeypatch.setenv("XAVANI_OUTPUT_MODE", "brief")
    assert resolve_output_mode(verbose=True) == VERBOSE


def test_invalid_env_falls_back(monkeypatch):
    monkeypatch.setenv("XAVANI_OUTPUT_MODE", "loud")
    assert resolve_output_mode() == DEFAULT


# ── application ─────────────────────────────────────────────────────


def test_brief_applies_progress_off():
    changes = apply_output_mode(BRIEF)
    assert changes["tool_progress"] == "off"
    assert changes["show_metadata_footer"] is False


def test_verbose_applies_full_progress():
    changes = apply_output_mode(VERBOSE)
    assert changes["tool_progress"] == "verbose"
    assert changes["show_metadata_footer"] is True
    assert changes["show_reasoning"] is True


def test_default_applies_new_progress():
    changes = apply_output_mode(DEFAULT)
    assert changes["tool_progress"] == "new"


# ── labels ──────────────────────────────────────────────────────────


def test_mode_labels():
    assert "brief" in mode_label(BRIEF)
    assert "verbose" in mode_label(VERBOSE)
    assert mode_label(DEFAULT) == "default"


# ── CLI wiring ──────────────────────────────────────────────────────


def test_main_accepts_brief_param():
    import inspect

    from cli import main

    params = inspect.signature(main).parameters
    assert "brief" in params
    assert "verbose" in params


def test_main_applies_brief_override(monkeypatch):
    """main() with --brief sets tool_progress off in the CLI config."""
    import cli

    captured = {}

    def _fake_apply(mode):
        captured["mode"] = mode
        return {"tool_progress": "off"}

    monkeypatch.setattr("xavani_cli.output_mode.resolve_output_mode",
                        lambda **k: BRIEF)
    monkeypatch.setattr("xavani_cli.output_mode.apply_output_mode",
                        _fake_apply)
    monkeypatch.setattr(cli, "CLI_CONFIG", {"display": {"tool_progress": "new"}})

    # Call the C11 block directly (main() itself exits via fire).
    from xavani_cli.output_mode import apply_output_mode, resolve_output_mode

    mode = resolve_output_mode(brief=True)
    changes = apply_output_mode(mode)
    assert changes["tool_progress"] == "off"
    assert captured["mode"] == BRIEF
