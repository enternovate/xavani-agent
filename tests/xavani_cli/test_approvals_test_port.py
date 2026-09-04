import importlib


def test_import_succeeds():
    assert importlib.import_module("xavani_cli.approvals_test") is not None


def test_exit_allow_is_zero():
    mod = importlib.import_module("xavani_cli.approvals_test")
    assert mod.EXIT_ALLOW == 0


def test_evaluate_command_returns_dict_for_echo():
    mod = importlib.import_module("xavani_cli.approvals_test")
    result = mod.evaluate_command("echo hello")
    assert isinstance(result, dict)
