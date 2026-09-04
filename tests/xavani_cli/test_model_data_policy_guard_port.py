import importlib


def test_model_data_policy_guard_imports():
    mod = importlib.import_module("xavani_cli.model_data_policy_guard")
    assert mod is not None


def test_model_data_policy_guard_main_entry():
    mod = importlib.import_module("xavani_cli.model_data_policy_guard")
    assert callable(mod.data_training_warning)
