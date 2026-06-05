# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the `xavani learn` CLI dispatch (v0.7.0 operator L10)."""

from __future__ import annotations

import argparse

from xavani_learner.learn_cli import cmd_learn


def _ns(**kw):
    return argparse.Namespace(**kw)


def test_show_seed_profile(capsys):
    cmd_learn(_ns(learn_command="show", target="clarity-precision"))
    out = capsys.readouterr().out
    assert "Clarity" in out
    assert "avoid" in out.lower()


def test_list_includes_seed_profiles(capsys):
    cmd_learn(_ns(learn_command="list"))
    out = capsys.readouterr().out
    assert "clarity-precision" in out
    assert "claude-craft" in out  # Claude design craft is learnable too


def test_show_unknown_profile(capsys):
    cmd_learn(_ns(learn_command="show", target="does-not-exist"))
    assert "no profile" in capsys.readouterr().out.lower()


def test_no_subcommand_prints_usage(capsys):
    cmd_learn(_ns(learn_command=None))
    assert "learn" in capsys.readouterr().out.lower()
