# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the `xavani wisdom` CLI (v1.0.0 ②)."""

from __future__ import annotations

from types import SimpleNamespace

from xavani_wisdom.cli import cmd_wisdom


def test_verdict_flags_downfall(capsys) -> None:
    cmd_wisdom(SimpleNamespace(wisdom_command="verdict", text=["borrow", "heavily", "go", "all", "in"]))
    out = capsys.readouterr().out
    assert "Oracle verdict" in out
    assert "risk=" in out
    assert "leverage" in out


def test_verdict_benign_has_no_downfall(capsys) -> None:
    cmd_wisdom(SimpleNamespace(wisdom_command="verdict", text=["write", "a", "unit", "test"]))
    out = capsys.readouterr().out
    assert "No known downfall pattern detected" in out


def test_corpus_lists_rise_and_fall(capsys) -> None:
    cmd_wisdom(SimpleNamespace(wisdom_command="corpus"))
    out = capsys.readouterr().out
    assert "Oracle corpus" in out
    assert "King Solomon" in out  # appears in both ascent and downfall
    assert "rose" in out and "fell" in out


def test_no_subcommand_prints_usage(capsys) -> None:
    cmd_wisdom(SimpleNamespace(wisdom_command=None))
    out = capsys.readouterr().out
    assert "Usage" in out
