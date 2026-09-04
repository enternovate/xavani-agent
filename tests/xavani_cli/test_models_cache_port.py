from __future__ import annotations


def test_clear_provider_models_cache_import_succeeds():
    from xavani_cli.models import clear_provider_models_cache

    assert callable(clear_provider_models_cache)


def test_provider_models_cache_path_filename(monkeypatch, tmp_path):
    monkeypatch.setenv("XAVANI_HOME", str(tmp_path))
    from xavani_cli.models import _provider_models_cache_path

    assert str(_provider_models_cache_path()).endswith("provider_models_cache.json")


def test_save_then_load_round_trip(monkeypatch, tmp_path):
    monkeypatch.setenv("XAVANI_HOME", str(tmp_path))
    from xavani_cli.models import _load_provider_models_cache, _save_provider_models_cache

    _save_provider_models_cache({"openrouter": {"models": ["a"], "cached_at": 1}})
    assert _load_provider_models_cache()["openrouter"] == {"models": ["a"], "cached_at": 1}
