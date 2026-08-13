# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for periodic long-term turn-bank retention (E103)."""

import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from agent.turn_bank import (
    add_completed_turn,
    completed_turns_from_messages,
    hydrate_turn_bank,
    parse_turn_bank_interval,
)

pytestmark = pytest.mark.unit


class _Store:
    memory_char_limit = 2_200


@pytest.fixture
def agent():
    return SimpleNamespace(
        _turn_bank_interval=2,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _memory_store=_Store(),
        _memory_manager=None,
    )


def test_missing_or_invalid_interval_preserves_disabled_behavior():
    assert parse_turn_bank_interval(None) == 0
    assert parse_turn_bank_interval("not-a-number") == 0
    assert parse_turn_bank_interval(0) == 0
    assert parse_turn_bank_interval(-2) == 0


def test_positive_interval_is_normalized():
    assert parse_turn_bank_interval("3") == 3
    assert parse_turn_bank_interval(4.9) == 4


def test_completed_turns_are_extracted_from_conversation_messages():
    messages = [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "working", "tool_calls": [{"id": "1"}]},
        {"role": "tool", "content": "done", "tool_call_id": "1"},
        {"role": "assistant", "content": "first answer"},
        {"role": "user", "content": "second"},
        {"role": "assistant", "content": "second answer"},
    ]

    assert completed_turns_from_messages(messages) == [
        ("first", "first answer"),
        ("second", "second answer"),
    ]


def test_turn_bank_writes_only_on_configured_boundary(agent):
    with patch("tools.memory_tool.memory_tool") as write:
        write.return_value = json.dumps({"success": True, "staged": False})

        assert add_completed_turn(agent, "first", "answer one") is False
        assert write.call_count == 0
        assert add_completed_turn(agent, "second", "answer two") is True

    write.assert_called_once()
    args = write.call_args.kwargs
    assert args["action"] == "add"
    assert args["target"] == "memory"
    assert "first" in args["content"]
    assert "second" in args["content"]
    assert args["store"] is agent._memory_store
    assert agent._turn_bank_pending == []
    assert agent._turn_bank_completed_count == 2


def test_failed_or_staged_write_keeps_pending_turns(agent):
    with patch("tools.memory_tool.memory_tool") as write:
        write.return_value = json.dumps({"success": True, "staged": True})
        assert add_completed_turn(agent, "first", "answer one") is False
        assert add_completed_turn(agent, "second", "answer two") is False

    assert len(agent._turn_bank_pending) == 2


@pytest.mark.parametrize("first_outcome", ["staged", "raises"])
def test_retry_writes_all_pending_turns_after_boundary_failure(agent, first_outcome):
    successful = json.dumps({"success": True, "staged": False})
    first_result = (
        json.dumps({"success": True, "staged": True})
        if first_outcome == "staged"
        else RuntimeError("memory write failed")
    )
    with patch("tools.memory_tool.memory_tool") as write:
        write.side_effect = [first_result, successful]
        assert add_completed_turn(agent, "first", "answer one") is False
        assert add_completed_turn(agent, "second", "answer two") is False
        assert add_completed_turn(agent, "third", "answer three") is True

    assert write.call_count == 2
    content = write.call_args.kwargs["content"]
    for text in ("first", "second", "third"):
        assert text in content
    assert agent._turn_bank_pending == []
    assert agent._turn_bank_completed_count == 2


def test_disabled_interval_does_not_touch_memory_write_path():
    agent = SimpleNamespace(
        _turn_bank_interval=0,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _memory_store=_Store(),
    )
    with patch("tools.memory_tool.memory_tool") as write:
        assert add_completed_turn(agent, "first", "answer") is False
    write.assert_not_called()
    assert agent._turn_bank_completed_count == 0


def test_exact_boundary_failed_write_is_recovered_after_restart(agent):
    with patch("tools.memory_tool.memory_tool") as write:
        write.return_value = json.dumps({"success": True, "staged": True})
        assert add_completed_turn(agent, "first", "answer one") is False
        assert add_completed_turn(agent, "second", "answer two") is False

    restarted = SimpleNamespace(
        _turn_bank_interval=2,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _memory_store=_Store(),
    )
    hydrate_turn_bank(
        restarted,
        [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "answer one"},
            {"role": "user", "content": "second"},
            {"role": "assistant", "content": "answer two"},
        ],
    )

    assert restarted._turn_bank_completed_count == 2
    assert restarted._turn_bank_pending == [
        ("first", "answer one"),
        ("second", "answer two"),
    ]


def test_successful_large_content_fallback_is_not_duplicated_after_restart():
    class _LargeContentStore:
        memory_char_limit = 70

        def __init__(self):
            self.memory_entries = []

        def _char_count(self, target):
            return len("\n§\n".join(self.memory_entries))

    store = _LargeContentStore()
    agent = SimpleNamespace(
        _turn_bank_interval=2,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _memory_store=store,
    )
    turns = [("first", "answer one"), ("second", "answer two")]

    def persist(**kwargs):
        kwargs["store"].memory_entries.append(kwargs["content"])
        return json.dumps({"success": True, "staged": False})

    with patch("tools.memory_tool.memory_tool", side_effect=persist) as write:
        for user_text, assistant_text in turns:
            assert add_completed_turn(agent, user_text, assistant_text) is (
                assistant_text == "answer two"
            )

    assert write.call_count == 2
    assert all("Long-term turn bank" not in entry for entry in store.memory_entries)

    restarted_store = _LargeContentStore()
    restarted_store.memory_entries = list(store.memory_entries)
    restarted = SimpleNamespace(
        _turn_bank_interval=2,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _memory_store=restarted_store,
    )
    hydrate_turn_bank(
        restarted,
        [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "answer one"},
            {"role": "user", "content": "second"},
            {"role": "assistant", "content": "answer two"},
        ],
    )

    assert restarted._turn_bank_completed_count == 2
    assert restarted._turn_bank_pending == []
