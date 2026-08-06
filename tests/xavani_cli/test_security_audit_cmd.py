# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the security audit command (C03).

The audit runs local checks only.  No network access, no real config
is read — the config loader is faked and file permissions are set on
real temp files.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

import xavani_cli.security_audit as audit


@pytest.fixture
def audit_home(tmp_path: Path, monkeypatch) -> Path:
    """Point XAVANI_HOME at a temp dir for the duration of the test."""
    monkeypatch.setenv("XAVANI_HOME", str(tmp_path))
    return tmp_path


def test_redact_secrets_enabled_passes(monkeypatch) -> None:
    """An enabled redaction flag must pass the audit check."""
    monkeypatch.setattr(
        audit, "load_config", lambda: {"security": {"redact_secrets": True}}
    )
    result = audit._check_redact_secrets()
    assert result["status"] == "PASS"


def test_redact_secrets_disabled_warns(monkeypatch) -> None:
    """A disabled redaction flag must warn."""
    monkeypatch.setattr(
        audit, "load_config", lambda: {"security": {"redact_secrets": False}}
    )
    result = audit._check_redact_secrets()
    assert result["status"] == "WARN"


def test_redact_secrets_unreadable_config_warns(monkeypatch) -> None:
    """An unreadable config must warn, not crash."""
    monkeypatch.setattr(audit, "load_config", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    result = audit._check_redact_secrets()
    assert result["status"] == "WARN"


def test_env_private_permissions_pass(audit_home: Path) -> None:
    """A private .env file must pass the permissions check."""
    env_path = audit_home / ".env"
    env_path.write_text("FAKE_KEY=fake\n", encoding="utf-8")
    os.chmod(env_path, 0o600)
    result = audit._check_file_permissions(env_path, ".env permissions")
    assert result["status"] == "PASS"


def test_env_world_readable_warns(audit_home: Path) -> None:
    """A world-readable .env file must warn."""
    env_path = audit_home / ".env"
    env_path.write_text("FAKE_KEY=fake\n", encoding="utf-8")
    os.chmod(env_path, 0o644)
    result = audit._check_file_permissions(env_path, ".env permissions")
    assert result["status"] == "WARN"


def test_missing_file_warns(audit_home: Path) -> None:
    """A missing sensitive file must warn, not crash."""
    result = audit._check_file_permissions(audit_home / "nope.env", ".env permissions")
    assert result["status"] == "WARN"


def test_cmd_security_audit_prints_report(audit_home: Path, monkeypatch, capsys) -> None:
    """The CLI entry point must print one line per check."""
    monkeypatch.setattr(
        audit, "load_config", lambda: {"security": {"redact_secrets": True}}
    )
    env_path = audit_home / ".env"
    env_path.write_text("FAKE_KEY=fake\n", encoding="utf-8")
    os.chmod(env_path, 0o600)
    cfg_path = audit_home / "config.yaml"
    cfg_path.write_text("security:\n  redact_secrets: true\n", encoding="utf-8")
    os.chmod(cfg_path, 0o600)
    audit.cmd_security_audit(None)
    out = capsys.readouterr().out
    assert "secret redaction" in out
    assert ".env permissions" in out
    assert "config.yaml permissions" in out
    assert "all checks passed" in out
