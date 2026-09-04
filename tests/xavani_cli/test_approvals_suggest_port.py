import importlib


def test_import_succeeds():
    assert importlib.import_module("xavani_cli.approvals_suggest") is not None


def test_parse_apply_indices_simple_spec():
    mod = importlib.import_module("xavani_cli.approvals_suggest")
    assert mod.parse_apply_indices("1,2", 3) == [0, 1]


def test_normalize_command_returns_nonempty():
    mod = importlib.import_module("xavani_cli.approvals_suggest")
    result = mod.normalize_command("echo hello")
    assert isinstance(result, str) and result.strip()
