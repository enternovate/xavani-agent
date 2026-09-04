import importlib


def test_personality_imports():
    mod = importlib.import_module("xavani_cli.personality")
    assert mod is not None


def test_persona_map_holds_pirate_and_noir():
    mod = importlib.import_module("xavani_cli.personality")
    assert "pirate" in mod.BUILTIN_PERSONALITIES
    assert "noir" in mod.BUILTIN_PERSONALITIES


def test_default_persona_accessor_returns_nonempty_string():
    mod = importlib.import_module("xavani_cli.personality")
    _, text = mod.resolve_personality("pirate")
    assert isinstance(text, str)
    assert text.strip() != ""
