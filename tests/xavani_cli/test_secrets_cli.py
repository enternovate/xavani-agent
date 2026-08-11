# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the secrets vault CLI (C04).

Secrets are stored in ``~/.xavani/.env`` and are never printed back.
These tests run against a temp Xavani home; no real config is touched.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import xavani_cli.secrets_cli as sec
from xavani_cli.config import load_env

pytestmark = pytest.mark.integration


@pytest.fixture
def vault_home(tmp_path: Path, monkeypatch) -> Path:
    """Point XAVANI_HOME at a temp dir for the duration of the test."""
    monkeypatch.setenv("XAVANI_HOME", str(tmp_path))
    return tmp_path


def test_add_stores_secret(vault_home: Path) -> None:
    """An added secret must persist to .env and load back."""
    sec.secrets_add("VAULT_TEST_KEY", "s3cr3t-value")
    env = load_env()
    assert env.get("VAULT_TEST_KEY") == "s3cr3t-value"
    raw = (vault_home / ".env").read_text(encoding="utf-8")
    assert "VAULT_TEST_KEY=s3cr3t-value" in raw


def test_add_invalid_name_raises(vault_home: Path) -> None:
    """An invalid secret name must raise ValueError."""
    with pytest.raises(ValueError):
        sec.secrets_add("NOT A VALID NAME", "x")


def test_list_returns_sorted_names(vault_home: Path) -> None:
    """List must return sorted names without values."""
    sec.secrets_add("B_KEY", "b-value")
    sec.secrets_add("A_KEY", "a-value")
    assert sec.secrets_list() == ["A_KEY", "B_KEY"]


def test_cmd_secrets_list_never_prints_values(vault_home: Path, capsys) -> None:
    """The list command must print names only, never values."""
    sec.secrets_add("HIDDEN_KEY", "top-secret-value")
    sec.cmd_secrets(None)
    out = capsys.readouterr().out
    assert "HIDDEN_KEY" in out
    assert "top-secret-value" not in out


def test_remove_deletes_secret(vault_home: Path) -> None:
    """Remove must delete the secret and report success."""
    sec.secrets_add("GONE_KEY", "value")
    assert sec.secrets_remove("GONE_KEY") is True
    assert "GONE_KEY" not in load_env()
    assert sec.secrets_remove("GONE_KEY") is False
