def test_repair_module_imports():
    import xavani_state_repair as mod

    assert mod is not None


def test_repair_exposes_main_entries():
    from xavani_state_repair import repair_state_db_schema

    assert callable(repair_state_db_schema)


def test_repair_missing_path_reports(tmp_path):
    from xavani_state_repair import repair_state_db_schema

    report = repair_state_db_schema(tmp_path / "missing.db")
    assert isinstance(report, dict)
    assert report.get("repaired") is False


def test_state_reexports_repair():
    from xavani_state import repair_state_db_schema

    assert callable(repair_state_db_schema)
