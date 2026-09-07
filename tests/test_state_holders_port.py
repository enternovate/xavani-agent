def test_holders_imports():
    import xavani_state_holders as mod

    assert mod is not None


def test_live_writer_probe_missing_path(tmp_path):
    from xavani_state_holders import live_writer_holds_db

    assert live_writer_holds_db(tmp_path / "missing.db", connect_repair_durable=None) in (True, False)


def test_foreign_holders_empty_for_missing(tmp_path):
    from xavani_state_holders import foreign_state_db_holders

    assert foreign_state_db_holders(tmp_path / "missing.db") == []
