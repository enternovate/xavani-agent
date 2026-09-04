import importlib
import inspect


def test_plugin_dev_imports():
    mod = importlib.import_module("xavani_cli.plugin_dev")
    assert mod is not None


def test_plugin_dev_doctor_report_is_class():
    mod = importlib.import_module("xavani_cli.plugin_dev")
    assert inspect.isclass(mod.DoctorReport)
