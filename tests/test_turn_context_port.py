from __future__ import annotations


def test_turn_context_imports() -> None:
    import agent.turn_context as tc

    assert tc is not None


def test_extract_api_content_sidecar_returns_sidecar() -> None:
    from agent.turn_context import extract_api_content_sidecar

    msg = {"role": "user", "content": "hi", "api_content": "ABC"}
    assert extract_api_content_sidecar(msg) == "ABC"


def test_extract_api_content_sidecar_plain_text_returns_none() -> None:
    from agent.turn_context import extract_api_content_sidecar

    assert extract_api_content_sidecar({"role": "user", "content": "hi"}) is None
