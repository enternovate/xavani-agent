# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for xavani_cli/tokens_cli.py — ``xavani tokens`` vault (Task 6.1)."""

from __future__ import annotations

import json
import os

import pytest

from xavani_cli.tokens_cli import (
    credentials_path,
    token_add,
    token_get,
    token_list,
    token_remove,
    token_usage,
    validate_tokens,
)

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _tmp_vault(tmp_path, monkeypatch):
    """Redirect the vault to a temp path."""
    monkeypatch.setattr("xavani_cli.tokens_cli.credentials_path", lambda: tmp_path / "credentials.json")
    return tmp_path


def test_add_and_get_roundtrip(tmp_path) -> None:
    token_add("ANTHROPIC", "sk-ant-123", provider="anthropic")
    assert token_get("ANTHROPIC") == "sk-ant-123"
    data = json.loads((tmp_path / "credentials.json").read_text(encoding="utf-8"))
    assert data["ANTHROPIC"]["provider"] == "anthropic"


def test_vault_file_has_0600_perms(tmp_path) -> None:
    token_add("OPENAI", "sk-456")
    mode = (tmp_path / "credentials.json").stat().st_mode & 0o777
    assert mode == 0o600


def test_list_hides_values(tmp_path) -> None:
    token_add("OPENAI", "sk-secret-value")
    entries = token_list()
    assert len(entries) == 1
    assert entries[0]["name"] == "OPENAI"
    assert "value" not in entries[0]
    assert entries[0]["length"] == len("sk-secret-value")


def test_remove_existing_and_missing(tmp_path) -> None:
    token_add("A", "1")
    assert token_remove("A") is True
    assert token_remove("A") is False
    assert token_list() == []


def test_add_rejects_blank(tmp_path) -> None:
    with pytest.raises(ValueError, match="name is required"):
        token_add("  ", "x")
    with pytest.raises(ValueError, match="value is required"):
        token_add("A", "   ")


def test_usage_summary(tmp_path) -> None:
    token_add("A", "1", provider="openai")
    usage = token_usage()
    assert usage["total"] == 1
    assert usage["has_provider_keys"] is True
    assert "credentials.json" in usage["path"]


def test_validate_tokens_empty_vault_healthy(tmp_path) -> None:
    assert validate_tokens() == []


def test_validate_tokens_flags_bad_perms(tmp_path) -> None:
    token_add("A", "1")
    os.chmod(tmp_path / "credentials.json", 0o644)
    problems = validate_tokens()
    assert any("0600" in p for p in problems)


def test_token_get_missing_returns_none(tmp_path) -> None:
    assert token_get("NOPE") is None


def test_legacy_string_entry_readable(tmp_path) -> None:
    (tmp_path / "credentials.json").write_text(json.dumps({"OLD": "legacy-value"}), encoding="utf-8")
    assert token_get("OLD") == "legacy-value"
    assert token_list()[0]["length"] == len("legacy-value")
