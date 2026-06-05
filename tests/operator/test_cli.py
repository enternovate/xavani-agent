# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the operator CLI dispatch (v0.7.0 operator U5)."""

from __future__ import annotations

import argparse

from xavani_operator.cli import cmd_operator


def _ns(**kw):
    return argparse.Namespace(**kw)


def test_init_creates_config_and_reports(tmp_path, capsys):
    cmd_operator(_ns(operator_command="init", path=str(tmp_path), name="Acme", force=False))
    assert (tmp_path / "xavani.product.yaml").exists()
    out = capsys.readouterr().out
    assert "xavani.product.yaml" in out


def test_init_on_existing_warns_without_raising(tmp_path, capsys):
    cmd_operator(_ns(operator_command="init", path=str(tmp_path), name="Acme", force=False))
    capsys.readouterr()  # clear
    # Second init must not raise; it warns the file exists.
    cmd_operator(_ns(operator_command="init", path=str(tmp_path), name="Acme", force=False))
    combined = "".join(capsys.readouterr())
    assert "exist" in combined.lower()


def test_status_reports_config_presence(tmp_path, capsys):
    cmd_operator(_ns(operator_command="init", path=str(tmp_path), name="Acme", force=False))
    capsys.readouterr()
    cmd_operator(_ns(operator_command="status", path=str(tmp_path)))
    out = capsys.readouterr().out
    assert "Acme" in out


def test_no_subcommand_prints_usage(capsys):
    cmd_operator(_ns(operator_command=None))
    out = capsys.readouterr().out
    assert "operator" in out.lower()
