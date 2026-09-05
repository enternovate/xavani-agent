import importlib


def test_dashboard_procs_imports():
    mod = importlib.import_module("xavani_cli.dashboard_procs")
    assert mod is not None


def test_dashboard_procs_main_entry():
    mod = importlib.import_module("xavani_cli.dashboard_procs")
    assert callable(mod._kill_stale_dashboard_processes)


def test_bounded_probe_run_callable():
    from xavani_cli._subprocess_compat import bounded_probe_run

    assert callable(bounded_probe_run)
