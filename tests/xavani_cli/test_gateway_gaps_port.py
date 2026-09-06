import xavani_cli.gateway as gateway


def test_gateway_update_helpers_importable():
    names = [
        "find_windows_gateway_services",
        "_capture_gateway_argv",
        "_prepare_profile_gateway_update_restart",
        "launch_detached_gateway_restart_by_cmdline",
        "_launchd_service_registered",
        "_locate_launchd_gateway_service",
        "launchd_gateway_labels_for_install",
        "_launchd_kickstart",
        "_wait_for_launchd_service_pid",
        "wait_for_launchd_gateway_supervision",
    ]
    for name in names:
        assert callable(getattr(gateway, name, None)), name


def test_find_windows_gateway_services_returns_list():
    assert isinstance(gateway.find_windows_gateway_services(), list)


def test_capture_gateway_argv_none_for_dead_pid():
    assert gateway._capture_gateway_argv(99999999) is None
