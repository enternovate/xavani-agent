from __future__ import annotations


def test_update_restart_recovery_import_succeeds():
    import xavani_cli.update_restart_recovery as update_restart_recovery

    assert update_restart_recovery is not None


def test_update_restart_recovery_exposes_main_entry():
    import xavani_cli.update_restart_recovery as update_restart_recovery

    assert callable(update_restart_recovery.main)
