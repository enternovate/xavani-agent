from __future__ import annotations


def test_message_metadata_append_message_imports() -> None:
    from agent.message_metadata import append_message

    messages: list = []
    append_message(messages, {"role": "user", "content": "hi"})
    assert len(messages) == 1
    assert messages[0]["timestamp"] is not None


def test_is_trivial_prompt() -> None:
    from agent.memory_provider import is_trivial_prompt

    assert is_trivial_prompt("") is True
    assert is_trivial_prompt("What is the capital of France?") is False


def test_automatic_compaction_status_message_default() -> None:
    from agent.context_engine import automatic_compaction_status_message

    assert (
        automatic_compaction_status_message(
            object(), phase="preflight", default_message="hello"
        )
        == "hello"
    )
