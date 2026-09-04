import importlib


def test_image_provenance_imports():
    mod = importlib.import_module("xavani_cli.image_provenance")
    assert mod is not None


def test_image_provenance_path_under_etc_xavani():
    mod = importlib.import_module("xavani_cli.image_provenance")
    assert str(mod.IMAGE_PROVENANCE_PATH).startswith("/etc/xavani")
