# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the `xavani finance` CLI dispatch (v0.7.0 operator M-Biz finance)."""

from __future__ import annotations

import argparse

from xavani_operator.finance.cli import cmd_finance


def _ns(**kw):
    return argparse.Namespace(**kw)


def test_pay_eft_renders_instruction(capsys):
    cmd_finance(_ns(finance_command="pay", method="eft", to="Supplier Co",
                    account="1234567890", branch="250655", rail=None, amount="2500", ref="P-1"))
    out = capsys.readouterr().out
    assert "Pay R2,500.00" in out
    assert "never moves money" in out.lower()


def test_pay_link_rail(capsys):
    cmd_finance(_ns(finance_command="pay", method="link", rail="yoco",
                    to=None, account=None, branch=None, amount="100", ref="P-2"))
    out = capsys.readouterr().out
    assert "yoco" in out
    assert "Pay R100.00" in out


def test_pay_link_bad_rail(capsys):
    cmd_finance(_ns(finance_command="pay", method="link", rail="paypal",
                    to=None, account=None, branch=None, amount="100", ref="P-3"))
    assert "unsupported" in capsys.readouterr().out.lower()


def test_no_subcommand_prints_usage(capsys):
    cmd_finance(_ns(finance_command=None))
    assert "finance" in capsys.readouterr().out.lower()
