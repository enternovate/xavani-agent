import sqlite3

import xavani_cli.backup as backup


def test_verify_sqlite_integrity_reports_missing_path_as_invalid(tmp_path):
    result = backup.verify_sqlite_integrity(tmp_path / "nope.db")
    assert result["valid"] is False
    assert result["size"] is None


def test_backfill_profile_envs_returns_list_on_empty_tmp_home(tmp_path, monkeypatch):
    import xavani_cli.profiles as profiles

    monkeypatch.setattr(profiles, "_get_default_xavani_home", lambda: tmp_path)
    assert profiles.backfill_profile_envs(quiet=True) == []


def test_quick_snapshot_root_imports():
    assert callable(backup._quick_snapshot_root)


def test_restore_cron_jobs_if_emptied_imports():
    assert callable(backup.restore_cron_jobs_if_emptied)
