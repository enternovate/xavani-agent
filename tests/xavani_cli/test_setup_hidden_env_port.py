import importlib


def test_setup_hidden_env_imports():
    mod = importlib.import_module("xavani_cli.setup_hidden_env")
    assert mod is not None


def test_is_setup_hidden_env_static():
    mod = importlib.import_module("xavani_cli.setup_hidden_env")
    assert mod.is_setup_hidden_env("DISCORD_HOME_CHANNEL") is True
    assert mod.is_setup_hidden_env("TELEGRAM_ALLOW_ALL_USERS") is True
    assert mod.is_setup_hidden_env("DISCORD_TOKEN") is False
