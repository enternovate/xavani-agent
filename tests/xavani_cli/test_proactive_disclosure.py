# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""G04: proactive disclosure — risk + rollback before risky operations."""

import json

import pytest

from xavani_cli.proactive_disclosure import (
    disclosure_categories,
    disclosure_for,
    format_disclosure,
)


def test_force_push_disclosure():
    d = disclosure_for("git push --force origin main")
    assert d is not None
    assert any("rewrites remote history" in r for r in d["risks"])
    assert d["rollback"]
    assert any("force-with-lease" in r for r in d["rollback"])


def test_rm_rf_disclosure():
    d = disclosure_for("rm -rf build/")
    assert d is not None
    assert any("unrecoverable" in r.lower() or "no undo" in r.lower() for r in d["risks"])


def test_dd_disclosure():
    d = disclosure_for("dd if=image.img of=/dev/sdb")
    assert d is not None
    assert any("device" in r.lower() for r in d["risks"])


def test_docker_prune_disclosure():
    d = disclosure_for("docker system prune -a")
    assert d is not None
    assert any("volume" in r.lower() or "container" in r.lower() for r in d["risks"])


def test_sql_delete_disclosure():
    d = disclosure_for("DELETE FROM users WHERE id = 1")
    assert d is not None
    assert any("transaction" in r.lower() for r in d["rollback"])


def test_kill_9_disclosure():
    d = disclosure_for("kill -9 1234")
    assert d is not None
    assert any("SIGTERM" in r for r in d["rollback"])


def test_safe_command_no_disclosure():
    assert disclosure_for("git status") is None
    assert disclosure_for("ls -la") is None
    assert disclosure_for("") is None


def test_format_disclosure_block():
    d = disclosure_for("rm -rf build/")
    assert d is not None
    block = format_disclosure(d)
    assert "Proactive disclosure" in block
    assert "Rollback plan" in block
    assert "•" in block


def test_categories_unique():
    cats = disclosure_categories()
    assert len(cats) == len(set(cats))


def test_approved_risky_command_carries_disclosure(monkeypatch):
    """check_all_command_guards attaches disclosure on user approval."""
    from tools.approval import check_all_command_guards

    monkeypatch.setenv("XAVANI_INTERACTIVE", "1")
    monkeypatch.setattr(
        "tools.approval.prompt_dangerous_approval",
        lambda *a, **k: "once",
    )
    result = check_all_command_guards("rm -rf build/", env_type="local")
    assert result["approved"] is True
    assert "disclosure" in result
    assert "Rollback plan" in result["disclosure"]


def test_approved_clean_command_no_disclosure(monkeypatch):
    from tools.approval import check_all_command_guards

    monkeypatch.setenv("XAVANI_INTERACTIVE", "1")
    result = check_all_command_guards("echo hello", env_type="local")
    assert result["approved"] is True
    assert "disclosure" not in result
