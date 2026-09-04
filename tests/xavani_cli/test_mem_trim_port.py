import xavani_cli.mem_trim as mem_trim


def test_mem_trim_import_succeeds():
    assert mem_trim is not None
    assert hasattr(mem_trim, "collect_memory_snapshot")
    assert hasattr(mem_trim, "trim_memory")


def test_cooldown_seconds_returns_positive_float():
    result = mem_trim._cooldown_seconds(30)
    assert isinstance(result, float)
    assert result > 0


def test_collect_memory_snapshot_returns_dict():
    snapshot = mem_trim.collect_memory_snapshot()
    assert isinstance(snapshot, dict)
