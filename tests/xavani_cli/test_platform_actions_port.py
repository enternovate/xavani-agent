from __future__ import annotations


def test_platform_actions_import_succeeds():
    import xavani_cli.platform_actions as platform_actions

    assert platform_actions is not None


def test_platform_actions_exposes_main_entry():
    import xavani_cli.platform_actions as platform_actions

    assert hasattr(platform_actions, "PlatformActions")
