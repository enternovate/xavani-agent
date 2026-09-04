from __future__ import annotations


def test_model_search_import_succeeds():
    import xavani_cli.model_search as model_search

    assert callable(model_search.model_search_text)


def test_model_search_text_returns_nonempty_string():
    from xavani_cli.model_search import model_search_text

    result = model_search_text("k3")

    assert isinstance(result, str) and len(result) > 0
