def test_portal_cli_imports():
    import xavani_cli.portal_cli as mod

    assert mod is not None
    assert callable(mod.add_parser)


def test_container_boot_imports():
    import xavani_cli.container_boot as mod

    assert mod is not None
    assert callable(mod.main)
    assert callable(mod.reconcile_profile_gateways)
