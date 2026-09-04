from xavani_cli.fallback_config import get_fallback_chain, resolve_entry_api_key


def test_import_succeeds():
    assert callable(get_fallback_chain)
    assert callable(resolve_entry_api_key)


def test_get_fallback_chain_none_returns_empty_list():
    assert get_fallback_chain(None) == []


def test_resolve_entry_api_key_none_returns_none():
    assert resolve_entry_api_key(None) is None
