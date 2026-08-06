# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Doctor token-vault check wiring (task 6.1)."""

from __future__ import annotations

from xavani_cli.doctor import _check_token_vault


def test_token_vault_healthy(monkeypatch, capsys) -> None:
    """An empty problem list renders the healthy check."""
    monkeypatch.setattr("xavani_cli.tokens_cli.validate_tokens", lambda: [])
    _check_token_vault([])
    out = capsys.readouterr().out
    assert "Token vault healthy" in out


def test_token_vault_reports_problems(monkeypatch, capsys) -> None:
    """Each vault problem renders as a warning and lands in the action list."""
    monkeypatch.setattr(
        "xavani_cli.tokens_cli.validate_tokens",
        lambda: ["credentials vault permissions are 0644, expected 0600: /tmp/vault"],
    )
    manual = []
    _check_token_vault(manual)
    out = capsys.readouterr().out
    assert "credentials vault permissions are 0644" in out
    assert any("token vault" in item.lower() for item in manual)


def test_token_vault_check_never_raises(monkeypatch, capsys) -> None:
    """A vault failure must not crash the rest of doctor."""
    def _boom():
        raise RuntimeError("vault broken")

    monkeypatch.setattr("xavani_cli.tokens_cli.validate_tokens", _boom)
    _check_token_vault([])
    out = capsys.readouterr().out
    assert "Token vault check failed" in out
