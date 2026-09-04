import importlib


def test_secret_prompt_imports():
    mod = importlib.import_module("xavani_cli.secret_prompt")
    assert mod is not None


def test_collect_masked_input_static():
    mod = importlib.import_module("xavani_cli.secret_prompt")
    chars = iter(["a", "b", "\n"])
    written = []
    result = mod._collect_masked_input(lambda: next(chars), written.append, "Password: ")
    assert result == "ab"
    assert written[0] == "Password: "
    assert written.count("*") == 2
