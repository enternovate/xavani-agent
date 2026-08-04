# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""C19: config diff — compare current config.yaml against a backup."""

import pytest

from xavani_cli.config import diff_config


@pytest.fixture
def hermetic_home(tmp_path, monkeypatch):
    """Isolate XAVANI_HOME and reset config caches per test."""
    monkeypatch.setenv("XAVANI_HOME", str(tmp_path / "home"))
    from xavani_cli import config as cfg

    cfg._LOAD_CONFIG_CACHE.clear()
    cfg._RAW_CONFIG_CACHE.clear()
    yield tmp_path
    cfg._LOAD_CONFIG_CACHE.clear()
    cfg._RAW_CONFIG_CACHE.clear()


def _write_config(monkeypatch, tmp_path, content: str):
    """Write config.yaml into the hermetic home."""
    from xavani_cli.config import ensure_xavani_home, get_config_path

    ensure_xavani_home()
    path = get_config_path()
    path.write_text(content, encoding="utf-8")
    from xavani_cli import config as cfg

    cfg._RAW_CONFIG_CACHE.clear()
    return path


def test_same_configs_reported_same(hermetic_home, monkeypatch):
    _write_config(monkeypatch, hermetic_home, "model:\n  default: a\n")
    backup = hermetic_home / "backup.yaml"
    backup.write_text("model:\n  default: a\n", encoding="utf-8")
    result = diff_config(str(backup))
    assert result["same"] is True
    assert result["added"] == []
    assert result["removed"] == []
    assert result["changed"] == []


def test_changed_value_reported(hermetic_home, monkeypatch):
    _write_config(monkeypatch, hermetic_home, "model:\n  default: a\n")
    backup = hermetic_home / "backup.yaml"
    backup.write_text("model:\n  default: b\n", encoding="utf-8")
    result = diff_config(str(backup))
    assert result["same"] is False
    assert "model.default" in result["changed"]


def test_added_and_removed_reported(hermetic_home, monkeypatch):
    _write_config(monkeypatch, hermetic_home, "model:\n  default: a\n")
    backup = hermetic_home / "backup.yaml"
    backup.write_text(
        "model:\n  default: a\nagent:\n  max_turns: 100\n", encoding="utf-8"
    )
    result = diff_config(str(backup))
    # agent.max_turns exists in backup, missing in current -> "added"
    # (present in the other file, absent now).
    assert "agent.max_turns" in result["added"]
    assert result["removed"] == []


def test_removed_key_reported(hermetic_home, monkeypatch):
    _write_config(monkeypatch, hermetic_home, "model:\n  default: a\nold_key: 1\n")
    backup = hermetic_home / "backup.yaml"
    backup.write_text("model:\n  default: a\n", encoding="utf-8")
    result = diff_config(str(backup))
    assert "old_key" in result["removed"]


def test_diff_against_defaults(hermetic_home, monkeypatch):
    """No backup path -> diff against built-in DEFAULT_CONFIG."""
    _write_config(monkeypatch, hermetic_home, "model:\n  default: some-model\n")
    result = diff_config()
    assert result["other_path"] == "defaults"
    assert "same" in result
    # The default config has many keys; a minimal user config shows them
    # as "added" (present in defaults, missing in user config).
    assert result["added"]


def test_missing_backup_returns_error(hermetic_home, monkeypatch):
    _write_config(monkeypatch, hermetic_home, "model:\n  default: a\n")
    result = diff_config("/nonexistent/backup.yaml")
    assert "error" in result
    assert "not found" in result["error"]


def test_invalid_backup_returns_error(hermetic_home, monkeypatch):
    _write_config(monkeypatch, hermetic_home, "model:\n  default: a\n")
    backup = hermetic_home / "bad.yaml"
    backup.write_text("model: [unclosed\n", encoding="utf-8")
    result = diff_config(str(backup))
    assert "error" in result
