import importlib


def test_toolset_validation_imports():
    mod = importlib.import_module("xavani_cli.toolset_validation")
    assert mod is not None


def test_validate_platform_toolsets_static():
    mod = importlib.import_module("xavani_cli.toolset_validation")
    assert mod.validate_platform_toolsets({}, lambda name: True) == []
    warnings = mod.validate_platform_toolsets({"cli": []}, lambda name: True)
    assert any("cli" in w for w in warnings)
