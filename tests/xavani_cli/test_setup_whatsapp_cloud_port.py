import importlib


def test_setup_whatsapp_cloud_imports():
    mod = importlib.import_module("xavani_cli.setup_whatsapp_cloud")
    assert mod is not None


def test_setup_whatsapp_cloud_main_entry():
    mod = importlib.import_module("xavani_cli.setup_whatsapp_cloud")
    assert callable(mod.run_whatsapp_cloud_setup)


def test_validate_phone_number_id_static_inputs():
    mod = importlib.import_module("xavani_cli.setup_whatsapp_cloud")
    assert mod._validate_phone_number_id("7794189252778687") == (True, None)
    ok, _ = mod._validate_phone_number_id("15556422442")
    assert ok is False
