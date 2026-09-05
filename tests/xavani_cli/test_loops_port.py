import xavani_cli.loops as loops


def test_loops_module_imports():
    assert loops is not None
    assert hasattr(loops, "LoopManager")


def test_loops_exposes_main_loop_entry():
    assert hasattr(loops, "LoopManager")
    mgr_cls = loops.LoopManager
    assert callable(mgr_cls)
    for method in ("set", "is_due", "fire_tick", "complete_tick", "status_line"):
        assert hasattr(mgr_cls, method), method


def test_format_interval_static_inputs():
    assert loops.format_interval(90) == "1m30s"
    assert loops.format_interval(5 * 60) == "5m"
    assert loops.parse_interval_token("5m") == 300
