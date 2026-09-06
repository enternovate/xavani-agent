from __future__ import annotations


def test_managed_uv_imports_and_exposes_ensure_uv():
    import xavani_cli.managed_uv as m

    assert callable(m.ensure_uv)


def test_model_catalog_imports_and_exposes_seed_cache():
    import xavani_cli.model_catalog as m

    assert callable(m.seed_cache_from_checkout)


def test_update_abort_recovery_imports_and_exposes_main_entry():
    import xavani_cli.update_abort_recovery as m

    assert callable(m._recover_gateway_restart_after_abort)


def test_scan_venv_blockers_imports_and_exposes_pausable_gateway():
    import xavani_cli._scan_venv_blockers as m

    assert callable(m._is_pausable_gateway)


def test_macos_tcc_anchor_imports_and_exposes_ensure_anchor():
    import xavani_cli.macos_tcc_anchor as m

    assert callable(m.ensure_tcc_anchor)
