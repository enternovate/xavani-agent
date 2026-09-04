import importlib


def test_init_command_imports():
    mod = importlib.import_module("xavani_cli.init_command")
    assert mod is not None


def test_build_init_prompt_for_cwd_returns_nonempty_string(tmp_path):
    mod = importlib.import_module("xavani_cli.init_command")
    result = mod.build_init_prompt_for_cwd(str(tmp_path))
    assert isinstance(result, str)
    assert result.strip() != ""
