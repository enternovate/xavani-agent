# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for periodic long-term turn-bank retention (E103)."""

import hashlib
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from agent.turn_bank import (
    _checkpoint_digest,
    _format_turn,
    _persisted_prefix_length,
    _turn_digest,
    add_completed_turn,
    completed_turns_from_messages,
    hydrate_turn_bank,
    parse_turn_bank_interval,
)

pytestmark = pytest.mark.unit


class _Store:
    memory_char_limit = 2_200
    memory_entries = []


@pytest.fixture
def agent():
    return SimpleNamespace(
        _turn_bank_interval=2,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _memory_enabled=True,
        _session_messages=[],
        _memory_store=_Store(),
        _memory_manager=None,
    )


def _messages(*turns):
    messages = []
    for user_text, assistant_text in turns:
        messages.append({"role": "user", "content": user_text})
        messages.append({"role": "assistant", "content": assistant_text})
    return messages


def test_missing_or_invalid_interval_preserves_disabled_behavior():
    assert parse_turn_bank_interval(None) == 0
    assert parse_turn_bank_interval("not-a-number") == 0
    assert parse_turn_bank_interval(0) == 0
    assert parse_turn_bank_interval(-2) == 0


def test_legacy_missing_progress_normalizes_covered_completed_count(tmp_path):
    state_path = tmp_path / "turn-bank.json"
    state_path.write_text(
        json.dumps({"version": 1, "completed_count": 1, "pending_count": 2}),
        encoding="utf-8",
    )
    restarted = SimpleNamespace(
        _turn_bank_interval=2,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _turn_bank_state_path=state_path,
        _memory_enabled=True,
        _session_messages=[],
        _memory_store=_Store(),
    )
    hydrate_turn_bank(
        restarted,
        _messages(("first", "answer one"), ("second", "answer two")),
    )

    assert restarted._turn_bank_completed_count == 2
    assert restarted._turn_bank_pending == [
        ("first", "answer one"),
        ("second", "answer two"),
    ]

    with patch("tools.memory_tool.memory_tool") as write:
        write.return_value = json.dumps({"success": True, "staged": False})
        assert add_completed_turn(restarted, "third", "answer three") is True

    write.assert_called_once()
    content = write.call_args.kwargs["content"]
    for text in ("first", "second", "third"):
        assert text in content
    assert restarted._turn_bank_pending == []
    assert restarted._turn_bank_completed_count == 3


def test_legacy_accurate_completed_count_is_preserved(tmp_path):
    state_path = tmp_path / "turn-bank.json"
    state_path.write_text(
        json.dumps(
            {
                "version": 1,
                "completed_count": 3,
                "pending_count": 3,
                "persisted_count": 0,
            }
        ),
        encoding="utf-8",
    )
    restarted = SimpleNamespace(
        _turn_bank_interval=2,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _turn_bank_state_path=state_path,
        _memory_enabled=True,
        _session_messages=[],
        _memory_store=_Store(),
    )
    hydrate_turn_bank(
        restarted,
        _messages(
            ("first", "answer one"),
            ("second", "answer two"),
            ("third", "answer three"),
        ),
    )

    assert restarted._turn_bank_completed_count == 3


class _Session:
    def __init__(self, messages):
        self._messages = messages

    def get_messages_as_conversation(self, session_id):
        return self._messages


def test_legacy_bounded_tail_recovers_full_pending_history(tmp_path):
    turns = [(f"prompt {i:02d}", f"answer {i:02d}") for i in range(1, 26)]
    state_path = tmp_path / "turn-bank.json"
    state_path.write_text(
        json.dumps({"version": 1, "completed_count": 25, "pending_count": 25}),
        encoding="utf-8",
    )
    restarted = SimpleNamespace(
        _turn_bank_interval=2,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _turn_bank_state_path=state_path,
        _memory_enabled=True,
        _session_messages=[],
        _memory_store=_Store(),
        _session_db=_Session(_messages(*turns)),
        session_id="sess",
    )
    hydrate_turn_bank(restarted, _messages(*turns[5:]))

    assert restarted._turn_bank_completed_count == 25
    assert restarted._turn_bank_pending == turns


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _RecordConn:
    def __init__(self, desc_rows):
        self._desc_rows = desc_rows
        self.calls = []

    def execute(self, sql, params):
        self.calls.append((sql, params))
        assert "LIMIT" in sql.upper(), f"unbounded SQL issued: {sql!r}"
        return _Rows(self._desc_rows)


class _SessionWithConn:
    def __init__(self, desc_rows):
        self._conn = _RecordConn(desc_rows)
        self.called_unbounded = False

    def get_messages_as_conversation(self, session_id):
        self.called_unbounded = True
        raise AssertionError("unbounded get_messages_as_conversation must not be used")


def _desc_rows(messages):
    rows = []
    for message in reversed(messages):
        rows.append(
            {
                "role": message.get("role"),
                "content": message.get("content"),
                "tool_calls": message.get("tool_calls", ""),
            }
        )
    return rows


def test_legacy_full_history_bounded_read_uses_trailing_window(tmp_path):
    turns = [(f"prompt {i:02d}", f"answer {i:02d}") for i in range(1, 26)]
    state_path = tmp_path / "turn-bank.json"
    state_path.write_text(
        json.dumps({"version": 1, "completed_count": 25, "pending_count": 25}),
        encoding="utf-8",
    )
    session_db = _SessionWithConn(_desc_rows(_messages(*turns)))
    restarted = SimpleNamespace(
        _turn_bank_interval=2,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _turn_bank_state_path=state_path,
        _memory_enabled=True,
        _session_messages=[],
        _memory_store=_Store(),
        _session_db=session_db,
        session_id="sess",
    )
    hydrate_turn_bank(restarted, _messages(*turns[5:]))

    assert restarted._turn_bank_completed_count == 25
    assert restarted._turn_bank_pending == turns
    assert session_db.called_unbounded is False
    assert session_db._conn.calls
    sql, params = session_db._conn.calls[0]
    assert "LIMIT" in sql.upper()
    assert params[0] == "sess"
    assert isinstance(params[1], int) and params[1] > 0


class _RaiseConn:
    def execute(self, sql, params):
        raise RuntimeError("db unavailable")


class _BadRowsConn:
    def execute(self, sql, params):
        return _Rows(
            [
                {"role": "user", "content": None},
                {"role": "assistant", "content": "\x00json:not-json"},
            ]
        )


@pytest.mark.parametrize("session_db", [_BadRowsConn], ids=["bad-rows"])
def test_legacy_bounded_read_raises_survives_null_content(session_db, tmp_path):
    turns = [(f"prompt {i:02d}", f"answer {i:02d}") for i in range(1, 6)]
    state_path = tmp_path / "turn-bank.json"
    state_path.write_text(
        json.dumps({"version": 1, "completed_count": 5, "pending_count": 5}),
        encoding="utf-8",
    )
    restarted = SimpleNamespace(
        _turn_bank_interval=2,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _turn_bank_state_path=state_path,
        _memory_enabled=True,
        _session_messages=[],
        _memory_store=_Store(),
        _session_db=session_db,
        session_id="sess",
    )
    hydrate_turn_bank(restarted, _messages(*turns[1:]))

    assert restarted._turn_bank_completed_count == 5
    assert restarted._turn_bank_pending == turns[1:]


def test_legacy_bounded_read_execute_error_keeps_supplied_tail(tmp_path):
    turns = [(f"prompt {i:02d}", f"answer {i:02d}") for i in range(1, 6)]
    state_path = tmp_path / "turn-bank.json"
    state_path.write_text(
        json.dumps({"version": 1, "completed_count": 5, "pending_count": 5}),
        encoding="utf-8",
    )
    restarted = SimpleNamespace(
        _turn_bank_interval=2,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _turn_bank_state_path=state_path,
        _memory_enabled=True,
        _session_messages=[],
        _memory_store=_Store(),
        _session_db=_RaiseConn(),
        session_id="sess",
    )
    hydrate_turn_bank(restarted, _messages(*turns[1:]))

    assert restarted._turn_bank_blocked is True
    assert restarted._turn_bank_completed_count == 5
    assert restarted._turn_bank_pending == turns[1:]


def test_legacy_post_checkpoint_reconstructs_full_pending_window(tmp_path):
    state_path = tmp_path / "turn-bank.json"
    state_path.write_text(
        json.dumps({"version": 1, "completed_count": 1, "pending_count": 2}),
        encoding="utf-8",
    )
    restarted = SimpleNamespace(
        _turn_bank_interval=2,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _turn_bank_state_path=state_path,
        _memory_enabled=True,
        _session_messages=[],
        _memory_store=_Store(),
    )
    hydrate_turn_bank(
        restarted,
        _messages(
            ("first", "answer one"),
            ("second", "answer two"),
            ("third", "answer three"),
        ),
    )

    assert restarted._turn_bank_completed_count == 3
    assert restarted._turn_bank_pending == [
        ("first", "answer one"),
        ("second", "answer two"),
        ("third", "answer three"),
    ]


def test_legacy_partial_progress_keeps_only_unpersisted_suffix(tmp_path):
    state_path = tmp_path / "turn-bank.json"
    state_path.write_text(
        json.dumps(
            {
                "version": 1,
                "completed_count": 1,
                "pending_count": 2,
                "persisted_count": 1,
            }
        ),
        encoding="utf-8",
    )
    store = _Store()
    store.memory_entries = [_format_turn("first", "answer one")]
    restarted = SimpleNamespace(
        _turn_bank_interval=2,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _turn_bank_state_path=state_path,
        _memory_enabled=True,
        _session_messages=[],
        _memory_store=store,
    )
    hydrate_turn_bank(
        restarted,
        _messages(("first", "answer one"), ("second", "answer two")),
    )

    assert restarted._turn_bank_completed_count == 2
    assert restarted._turn_bank_pending == [("second", "answer two")]


def test_legacy_stale_persisted_count_keeps_both_turns_pending(tmp_path):
    state_path = tmp_path / "turn-bank.json"
    state_path.write_text(
        json.dumps(
            {
                "version": 1,
                "completed_count": 1,
                "pending_count": 2,
                "persisted_count": 1,
            }
        ),
        encoding="utf-8",
    )
    restarted = SimpleNamespace(
        _turn_bank_interval=2,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _turn_bank_state_path=state_path,
        _memory_enabled=True,
        _session_messages=[],
        _memory_store=_Store(),
    )
    hydrate_turn_bank(
        restarted,
        _messages(("first", "answer one"), ("second", "answer two")),
    )

    assert restarted._turn_bank_completed_count == 2
    assert restarted._turn_bank_pending == [
        ("first", "answer one"),
        ("second", "answer two"),
    ]


def test_legacy_older_identical_entry_keeps_candidate_pending(tmp_path):
    state_path = tmp_path / "turn-bank.json"
    state_path.write_text(
        json.dumps({"version": 1, "completed_count": 3, "pending_count": 2}),
        encoding="utf-8",
    )
    store = _Store()
    store.memory_entries = [_format_turn("same", "answer")]
    restarted = SimpleNamespace(
        _turn_bank_interval=2,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _turn_bank_state_path=state_path,
        _memory_enabled=True,
        _session_messages=[],
        _memory_store=store,
    )
    hydrate_turn_bank(
        restarted,
        _messages(
            ("same", "answer"),
            ("same", "answer"),
            ("different", "answer"),
        ),
    )

    assert restarted._turn_bank_completed_count == 3
    assert restarted._turn_bank_pending == [
        ("same", "answer"),
        ("different", "answer"),
    ]


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


def test_compression_summary_standalone_assistant_message_is_not_a_completed_turn():
    summary_body = (
        "[CONTEXT COMPACTION — REFERENCE ONLY] Earlier turns were compacted into "
        "the summary below.\n\n- The user asked about project setup.\n"
        "- The assistant configured the environment."
    )
    messages = [
        {"role": "user", "content": "first question"},
        {"role": "assistant", "content": "first answer"},
        {"role": "assistant", "content": summary_body},
        {"role": "user", "content": "second question"},
        {"role": "assistant", "content": "second answer"},
    ]

    assert completed_turns_from_messages(messages) == [
        ("first question", "first answer"),
        ("second question", "second answer"),
    ]


def test_compression_summary_merged_into_tail_user_message_keeps_real_suffix():
    summary_body = (
        "[CONTEXT COMPACTION — REFERENCE ONLY] Earlier turns were compacted into "
        "the summary below.\n\n- The user asked about project setup.\n"
        "- The assistant configured the environment."
    )
    end_marker = (
        "\n\n--- END OF CONTEXT SUMMARY — respond to the message below, "
        "not the summary above ---"
    )
    merged_text = summary_body + end_marker + "\n\nnow deploy it to staging"
    messages = [
        {"role": "user", "content": "first question"},
        {"role": "assistant", "content": "first answer"},
        {"role": "user", "content": merged_text},
        {"role": "assistant", "content": "second answer"},
    ]

    assert completed_turns_from_messages(messages) == [
        ("first question", "first answer"),
        ("now deploy it to staging", "second answer"),
    ]


def test_standalone_user_summary_creates_no_completed_turn():
    summary_body = (
        "[CONTEXT COMPACTION — REFERENCE ONLY] Earlier turns were compacted into "
        "the summary below.\n\n- The user asked about project setup."
    )
    messages = [
        {"role": "user", "content": summary_body},
        {"role": "assistant", "content": "post-summary answer"},
    ]

    assert completed_turns_from_messages(messages) == []


def test_preserved_task_list_after_outer_request_is_not_a_turn():
    messages = [
        {"role": "user", "content": "outer request"},
        {"role": "assistant", "content": "first answer"},
        {
            "role": "user",
            "content": "[Your active task list was preserved across context compression]",
        },
        {"role": "assistant", "content": "final answer"},
    ]

    assert completed_turns_from_messages(messages) == [
        ("outer request", "first answer"),
    ]


def test_genuine_first_request_starting_with_task_list_marker_is_kept():
    messages = [
        {
            "role": "user",
            "content": (
                "[Your active task list was preserved across context compression]\n"
                "now refactor the auth module"
            ),
        },
        {"role": "assistant", "content": "refactor done"},
    ]

    assert completed_turns_from_messages(messages) == [
        (
            "[Your active task list was preserved across context compression]\n"
            "now refactor the auth module",
            "refactor done",
        ),
    ]


def test_length_continuation_fragments_concatenate_into_one_turn():
    control = (
        "[System: Your previous response was truncated by the output length limit. "
        "Continue exactly where you left off. Do not restart or repeat prior text. "
        "Finish the answer directly.]"
    )
    messages = [
        {"role": "user", "content": "outer"},
        {"role": "assistant", "content": "fragment one"},
        {"role": "user", "content": control},
        {"role": "assistant", "content": "fragment two"},
    ]

    assert completed_turns_from_messages(messages) == [
        ("outer", "fragment onefragment two"),
    ]


def test_codex_ack_continuation_discards_ack_text():
    control = (
        "[System: Continue now. Execute the required tool calls and only send "
        "your final answer after completing the task.]"
    )
    messages = [
        {"role": "user", "content": "outer"},
        {"role": "assistant", "content": "ack text"},
        {"role": "user", "content": control},
        {"role": "assistant", "content": "final answer"},
    ]

    assert completed_turns_from_messages(messages) == [
        ("outer", "final answer"),
    ]


def test_max_iteration_summary_yields_no_completed_turn():
    control = (
        "You've reached the maximum number of tool-calling iterations allowed. "
        "Please provide a final response summarizing what you've found and "
        "accomplished so far, without calling any more tools."
    )
    messages = [
        {"role": "user", "content": "outer"},
        {"role": "assistant", "content": "partial work"},
        {"role": "user", "content": control},
        {"role": "assistant", "content": "summary of partial work"},
    ]

    assert completed_turns_from_messages(messages) == []


def test_kanban_stop_nudge_is_not_a_turn():
    control = (
        "[System: You are a Xavani kanban worker. A plain-text reply is NOT a "
        "terminal state for the board.\n\n"
        "Task `this task` is still `running`. Ending now without a board tool "
        "causes a protocol violation (clean exit with no "
        "`kanban_complete` / `kanban_block`).\n\n"
        "Do this immediately in your next response - do not narrate intent:\n"
        "1. Finish any remaining deliverable (write the required file(s) now).\n"
        "2. Call `kanban_complete(summary=..., artifacts=[...])` if the work "
        "is done, OR `kanban_block(reason=...)` if you are blocked.\n\n"
        "Never end a turn with only a promise of future action. Repeated "
        "protocol violations will block this task and require manual "
        "intervention.]"
    )
    messages = [
        {"role": "user", "content": "outer"},
        {"role": "assistant", "content": "work done"},
        {"role": "user", "content": control, "_kanban_stop_synthetic": True},
        {"role": "assistant", "content": "final answer"},
    ]

    assert completed_turns_from_messages(messages) == [
        ("outer", "final answer"),
    ]

    plain = [{k: v for k, v in m.items() if not k.startswith("_")} for m in messages]

    assert completed_turns_from_messages(plain) == [
        ("outer", "final answer"),
    ]


def test_empty_recovery_nudge_is_not_a_turn():
    control = (
        "You just executed tool calls but returned an "
        "empty response. Please process the tool "
        "results above and continue with the task."
    )
    messages = [
        {"role": "user", "content": "outer"},
        {"role": "assistant", "content": "partial"},
        {"role": "user", "content": control, "_empty_recovery_synthetic": True},
        {"role": "assistant", "content": "final answer"},
    ]

    assert completed_turns_from_messages(messages) == [
        ("outer", "final answer"),
    ]

    plain = [{k: v for k, v in m.items() if not k.startswith("_")} for m in messages]

    assert completed_turns_from_messages(plain) == [
        ("outer", "final answer"),
    ]


def test_thinking_prefill_is_not_the_final_answer():
    prefill = "<think>weigh the options silently</think>"
    messages = [
        {"role": "user", "content": "outer"},
        {"role": "assistant", "content": prefill, "_thinking_prefill": True},
        {"role": "assistant", "content": "real answer"},
    ]

    assert completed_turns_from_messages(messages) == [
        ("outer", "real answer"),
    ]

    plain = [{k: v for k, v in m.items() if not k.startswith("_")} for m in messages]

    assert completed_turns_from_messages(plain) == [
        ("outer", "real answer"),
    ]


def test_empty_terminal_sentinel_yields_no_turn():
    flagged = [
        {"role": "user", "content": "outer"},
        {
            "role": "assistant",
            "content": "(empty)",
            "_empty_terminal_sentinel": True,
        },
    ]

    assert completed_turns_from_messages(flagged) == []

    unflagged = [
        {"role": "user", "content": "outer"},
        {"role": "assistant", "content": "(empty)"},
    ]

    assert completed_turns_from_messages(unflagged) == []


def test_mcp_reload_marker_between_turns_creates_no_turn():
    reload_marker = (
        "[IMPORTANT: MCP servers have been reloaded. 2 servers changed. "
        "The tool list for this conversation has been updated accordingly.]"
    )
    messages = [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "answer one"},
        {"role": "user", "content": reload_marker},
        {"role": "user", "content": "second"},
        {"role": "assistant", "content": "answer two"},
    ]

    assert completed_turns_from_messages(messages) == [
        ("first", "answer one"),
        ("second", "answer two"),
    ]


def test_mcp_reload_before_first_request_creates_no_turn():
    reload_marker = (
        "[IMPORTANT: MCP servers have been reloaded. 2 servers changed. "
        "The tool list for this conversation has been updated accordingly.]"
    )
    messages = [
        {"role": "user", "content": reload_marker},
        {"role": "user", "content": "real"},
        {"role": "assistant", "content": "answer"},
    ]

    assert completed_turns_from_messages(messages) == [
        ("real", "answer"),
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


def test_integer_staged_value_keeps_pending_turns(agent):
    with patch("tools.memory_tool.memory_tool") as write:
        write.return_value = json.dumps({"success": True, "staged": 1})
        assert add_completed_turn(agent, "first", "answer one") is False
        assert add_completed_turn(agent, "second", "answer two") is False

    assert len(agent._turn_bank_pending) == 2


def test_string_staged_value_keeps_pending_turns(agent):
    with patch("tools.memory_tool.memory_tool") as write:
        write.return_value = json.dumps({"success": True, "staged": "true"})
        assert add_completed_turn(agent, "first", "answer one") is False
        assert add_completed_turn(agent, "second", "answer two") is False

    assert len(agent._turn_bank_pending) == 2


def test_null_staged_value_keeps_pending_turns(agent):
    with patch("tools.memory_tool.memory_tool") as write:
        write.return_value = json.dumps({"success": True, "staged": None})
        assert add_completed_turn(agent, "first", "answer one") is False
        assert add_completed_turn(agent, "second", "answer two") is False

    assert len(agent._turn_bank_pending) == 2


def test_direct_success_result_banks_boundary(agent):
    with patch("tools.memory_tool.memory_tool") as write:
        write.return_value = json.dumps({"success": True})
        assert add_completed_turn(agent, "first", "answer one") is False
        assert add_completed_turn(agent, "second", "answer two") is True

    assert agent._turn_bank_pending == []


@pytest.mark.parametrize(
    "result",
    [
        '{"success":1}',
        '{"success":"true"}',
        '{"staged":false}',
        '[{"success":true}]',
        "not json at all",
    ],
)
def test_invalid_memory_results_keep_pending_turns(agent, result):
    with patch("tools.memory_tool.memory_tool") as write:
        write.return_value = result
        assert add_completed_turn(agent, "first", "answer one") is False
        assert add_completed_turn(agent, "second", "answer two") is False

    assert len(agent._turn_bank_pending) == 2


def test_failed_or_staged_write_keeps_pending_turns(agent):
    with patch("tools.memory_tool.memory_tool") as write:
        write.return_value = json.dumps({"success": True, "staged": True})
        assert add_completed_turn(agent, "first", "answer one") is False
        assert add_completed_turn(agent, "second", "answer two") is False

    assert len(agent._turn_bank_pending) == 2


def test_incomplete_request_does_not_reuse_earlier_identical_response(tmp_path):
    store = _Store()
    store.memory_entries = [_format_turn("same question", "earlier answer")]
    agent = SimpleNamespace(
        _turn_bank_interval=1,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _turn_bank_state_path=tmp_path / "turn-bank.json",
        _memory_enabled=True,
        _memory_store=store,
        _session_messages=[
            {"role": "user", "content": "same question"},
            {"role": "assistant", "content": "earlier answer"},
        ],
    )

    with patch("tools.memory_tool.memory_tool") as write:
        assert add_completed_turn(agent, "same question", "") is False

    write.assert_not_called()
    assert store.memory_entries == [_format_turn("same question", "earlier answer")]


@pytest.mark.parametrize(
    "prefix",
    [
        "[System: Your previous response was truncated",
        "[System: Continue now.",
        "[Your active task list was preserved across context compression]",
        "[IMPORTANT: MCP servers have been reloaded.",
        "You've reached the maximum number",
        "You just executed tool calls but returned an empty response",
    ],
)
def test_genuine_requests_with_control_prefixes_are_preserved(prefix):
    messages = [
        {"role": "user", "content": prefix + "\nplease help"},
        {"role": "assistant", "content": "sure"},
    ]

    assert completed_turns_from_messages(messages) == [
        (prefix + "\nplease help", "sure"),
    ]


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
    assert agent._turn_bank_completed_count == 3


def test_oversized_turn_format_preserves_head_tail_and_marks_truncation():
    user_text = "U" * 600 + "USER_MIDDLE" + "u" * 600 + "USER_TAIL"
    assistant_text = "A" * 1_100 + "ASSISTANT_MIDDLE" + "a" * 1_100 + "ASSISTANT_TAIL"

    formatted = _format_turn(user_text, assistant_text)
    user_part, assistant_part = formatted.split("\nAssistant: ", 1)
    user_value = user_part.removeprefix("User: ")

    assert "...[truncated]..." in formatted
    assert user_value.startswith(user_text[:100])
    assert user_value.endswith(user_text[-100:])
    assert len(user_value) == 700
    assert assistant_part.startswith(assistant_text[:100])
    assert assistant_part.endswith(assistant_text[-100:])
    assert len(assistant_part) == 1_300


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


def test_memory_disabled_agent_does_not_write_turn_bank(tmp_path):
    agent = SimpleNamespace(
        _turn_bank_interval=2,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _turn_bank_state_path=tmp_path / "turn-bank.json",
        _memory_enabled=False,
        _session_messages=[],
        _memory_store=_Store(),
    )
    with patch("tools.memory_tool.memory_tool") as write:
        assert add_completed_turn(agent, "first", "answer one") is False
        assert add_completed_turn(agent, "second", "answer two") is False

    write.assert_not_called()
    assert agent._turn_bank_completed_count == 0
    assert agent._turn_bank_pending == []
    assert not agent._turn_bank_state_path.exists()


def test_memory_disabled_agent_does_not_hydrate_turn_bank(tmp_path):
    state_path = tmp_path / "turn-bank.json"
    state_path.write_text(
        json.dumps(
            {
                "version": 1,
                "completed_count": 1,
                "pending_count": 1,
                "persisted_count": 0,
            }
        ),
        encoding="utf-8",
    )
    agent = SimpleNamespace(
        _turn_bank_interval=2,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _turn_bank_state_path=state_path,
        _memory_enabled=False,
        _session_messages=[],
        _memory_store=_Store(),
    )
    hydrate_turn_bank(agent, _messages(("first", "answer one")))

    assert agent._turn_bank_completed_count == 0
    assert agent._turn_bank_pending == []


def test_exact_boundary_failed_write_is_recovered_after_restart(agent):
    with patch("tools.memory_tool.memory_tool") as write:
        write.return_value = json.dumps({"success": True, "staged": True})
        assert add_completed_turn(agent, "first", "answer one") is False
        assert add_completed_turn(agent, "second", "answer two") is False

    restarted = SimpleNamespace(
        _turn_bank_interval=2,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _memory_enabled=True,
        _session_messages=[],
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
        _memory_enabled=True,
        _session_messages=[],
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
        _memory_enabled=True,
        _session_messages=[],
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


def test_partial_large_content_fallback_retries_only_unpersisted_suffix_after_restart(
    tmp_path,
):
    class _LargeContentStore:
        memory_char_limit = 1

        def __init__(self):
            self.memory_entries = []

        def _char_count(self, target):
            return len("\n§\n".join(self.memory_entries))

    store = _LargeContentStore()
    agent = SimpleNamespace(
        _turn_bank_interval=2,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _turn_bank_state_path=tmp_path / "turn-bank.json",
        _memory_enabled=True,
        _session_messages=[],
        _memory_store=store,
    )
    successful = json.dumps({"success": True, "staged": False})

    def persist(**kwargs):
        if kwargs["content"].startswith("User: first"):
            kwargs["store"].memory_entries.append(kwargs["content"])
            return successful
        raise RuntimeError("memory write failed")

    with patch("tools.memory_tool.memory_tool", side_effect=persist):
        assert add_completed_turn(agent, "first", "answer one") is False
        assert add_completed_turn(agent, "second", "answer two") is False

    state = json.loads(agent._turn_bank_state_path.read_text(encoding="utf-8"))
    from agent.turn_bank import _checkpoint_digest, _pending_digest, _turn_digest

    assert state["version"] == 2
    assert state["completed_count"] == 2
    assert state["pending_count"] == 1
    assert state["write_due"] is True
    turn_digest = _turn_digest("second", "answer two")
    assert state["checkpoint_digest"] == _checkpoint_digest(2, turn_digest)
    assert state["pending_digest"] == _pending_digest(
        2, [("second", "answer two")]
    )

    restarted_store = _LargeContentStore()
    restarted_store.memory_entries = list(store.memory_entries)
    restarted = SimpleNamespace(
        _turn_bank_interval=2,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _turn_bank_state_path=agent._turn_bank_state_path,
        _memory_enabled=True,
        _session_messages=[],
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
    assert restarted._turn_bank_pending == [("second", "answer two")]


def test_partial_large_content_fallback_retries_only_unpersisted_suffix_in_same_agent():
    class _LargeContentStore:
        memory_char_limit = 1

        def __init__(self):
            self.memory_entries = []

        def _char_count(self, target):
            return len("\n§\n".join(self.memory_entries))

    store = _LargeContentStore()
    agent = SimpleNamespace(
        _turn_bank_interval=2,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _memory_enabled=True,
        _session_messages=[],
        _memory_store=store,
    )
    successful = json.dumps({"success": True, "staged": False})
    attempts = []

    def persist(**kwargs):
        content = kwargs["content"]
        attempts.append(content)
        if content.startswith("User: first"):
            kwargs["store"].memory_entries.append(content)
            return successful
        if content.startswith("User: second") and len(attempts) == 2:
            raise RuntimeError("memory write failed")
        kwargs["store"].memory_entries.append(content)
        return successful

    with patch("tools.memory_tool.memory_tool", side_effect=persist) as write:
        assert add_completed_turn(agent, "first", "answer one") is False
        assert add_completed_turn(agent, "second", "answer two") is False
        assert agent._turn_bank_pending == [("second", "answer two")]
        assert add_completed_turn(agent, "third", "answer three") is True

    assert write.call_count == 4
    assert [entry.splitlines()[0] for entry in attempts] == [
        "User: first",
        "User: second",
        "User: second",
        "User: third",
    ]
    assert store.memory_entries == [
        "User: first\nAssistant: answer one",
        "User: second\nAssistant: answer two",
        "User: third\nAssistant: answer three",
    ]
    assert agent._turn_bank_pending == []
    assert agent._turn_bank_completed_count == 3


def test_duplicate_fallback_single_entry_proves_only_first_occurrence(tmp_path):
    class _LargeContentStore:
        memory_char_limit = 1

        def __init__(self):
            self.memory_entries = []

        def _char_count(self, target):
            return len("\n§\n".join(self.memory_entries))

    store = _LargeContentStore()
    agent = SimpleNamespace(
        _turn_bank_interval=2,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _turn_bank_state_path=tmp_path / "turn-bank.json",
        _memory_enabled=True,
        _session_messages=[],
        _memory_store=store,
    )
    successful = json.dumps({"success": True, "staged": False})
    state_writes_broken = []

    def persist(**kwargs):
        if kwargs["content"] in kwargs["store"].memory_entries:
            return successful
        kwargs["store"].memory_entries.append(kwargs["content"])
        state_writes_broken.append(True)
        return successful

    def replace(source, destination):
        if state_writes_broken:
            raise OSError("state write failed")
        from utils import atomic_replace

        atomic_replace(source, destination)

    with patch(
        "tools.memory_tool.memory_tool", side_effect=persist
    ), patch("agent.turn_bank.atomic_replace", side_effect=replace):
        assert add_completed_turn(agent, "same", "answer") is False
        assert add_completed_turn(agent, "same", "answer") is True

    assert len(store.memory_entries) == 1

    restarted_store = _LargeContentStore()
    restarted_store.memory_entries = list(store.memory_entries)
    restarted = SimpleNamespace(
        _turn_bank_interval=2,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _turn_bank_state_path=agent._turn_bank_state_path,
        _memory_enabled=True,
        _session_messages=[],
        _memory_store=restarted_store,
    )
    hydrate_turn_bank(
        restarted,
        [
            {"role": "user", "content": "same"},
            {"role": "assistant", "content": "answer"},
            {"role": "user", "content": "same"},
            {"role": "assistant", "content": "answer"},
        ],
    )

    assert restarted._turn_bank_completed_count == 2
    assert restarted._turn_bank_pending == [("same", "answer")]


def test_version_two_round_trip_state_writes_digests_and_write_due(tmp_path):
    from agent.turn_bank import _checkpoint_digest, _pending_digest, _turn_digest

    agent = SimpleNamespace(
        _turn_bank_interval=2,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _memory_enabled=True,
        _session_messages=[],
        _memory_store=_Store(),
        _turn_bank_state_path=tmp_path / "turn-bank.json",
    )
    with patch("tools.memory_tool.memory_tool") as write:
        write.return_value = json.dumps({"success": True, "staged": False})
        assert add_completed_turn(agent, "first", "answer one") is False

    state = json.loads(agent._turn_bank_state_path.read_text(encoding="utf-8"))
    assert state["version"] == 2
    assert state["completed_count"] == 1
    assert state["pending_count"] == 1
    assert len(state["checkpoint_digest"]) == 64
    assert len(state["pending_digest"]) == 64
    assert state["write_due"] is False

    raw = agent._turn_bank_state_path.read_text(encoding="utf-8")
    assert "first" not in raw
    assert "answer one" not in raw

    turn_digest = _turn_digest("first", "answer one")
    assert _checkpoint_digest(1, turn_digest) != _checkpoint_digest(2, turn_digest)
    assert state["checkpoint_digest"] == _checkpoint_digest(1, turn_digest)
    assert _pending_digest(1, [("first", "answer one")]) != _pending_digest(
        2, [("first", "answer one")]
    )
    assert state["pending_digest"] == _pending_digest(1, [("first", "answer one")])


def _valid_v2_state(completed=2, pending=2, write_due=False):
    return {
        "version": 2,
        "completed_count": completed,
        "pending_count": pending,
        "checkpoint_digest": _CHECKPOINT_ZERO,
        "pending_digest": _CHECKPOINT_ZERO,
        "write_due": write_due,
    }


_CHECKPOINT_ZERO = "0" * 64


def _restarted_agent(tmp_path, state_path, store=None):
    return SimpleNamespace(
        _turn_bank_interval=2,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _turn_bank_state_path=state_path,
        _memory_enabled=True,
        _session_messages=[],
        _memory_store=store if store is not None else _Store(),
    )


def test_version_two_future_state_blocks_recovery_and_memory_writes(tmp_path):
    future_path = tmp_path / "future-bank.json"
    ancestor_path = tmp_path / "ancestor-bank.json"
    future_path.write_text(
        json.dumps({"version": 99, "completed_count": 9, "pending_count": 9}),
        encoding="utf-8",
    )
    ancestor_path.write_text(
        json.dumps(_valid_v2_state(completed=9, pending=9)),
        encoding="utf-8",
    )
    restarted = _restarted_agent(tmp_path, future_path)
    hydrate_turn_bank(
        restarted,
        _messages(("first", "answer one"), ("second", "answer two")),
    )

    assert restarted._turn_bank_completed_count == 0
    assert restarted._turn_bank_pending == []
    with patch("tools.memory_tool.memory_tool") as write:
        assert add_completed_turn(restarted, "third", "answer three") is False
    write.assert_not_called()
    assert json.loads(future_path.read_text(encoding="utf-8")) == {
        "version": 99,
        "completed_count": 9,
        "pending_count": 9,
    }
    assert json.loads(ancestor_path.read_text(encoding="utf-8")) == _valid_v2_state(
        completed=9, pending=9
    )


def test_version_two_missing_digest_uses_safe_history_fallback(tmp_path):
    state_path = tmp_path / "turn-bank.json"
    payload = _valid_v2_state(completed=2, pending=0)
    payload.pop("checkpoint_digest")
    state_path.write_text(json.dumps(payload), encoding="utf-8")
    restarted = _restarted_agent(tmp_path, state_path)
    hydrate_turn_bank(
        restarted,
        _messages(("first", "answer one"), ("second", "answer two")),
    )

    assert restarted._turn_bank_completed_count == 2
    assert restarted._turn_bank_pending == [
        ("first", "answer one"),
        ("second", "answer two"),
    ]


def test_version_two_checkpoint_digest_mismatch_rebuilds_from_history(tmp_path):
    turns = [(f"prompt {i:02d}", f"answer {i:02d}") for i in range(1, 6)]
    state_path = tmp_path / "turn-bank.json"
    payload = _valid_v2_state(completed=3, pending=3)
    payload["checkpoint_digest"] = "1" * 64
    state_path.write_text(json.dumps(payload), encoding="utf-8")
    restarted = _restarted_agent(tmp_path, state_path)
    hydrate_turn_bank(restarted, _messages(*turns))

    assert restarted._turn_bank_completed_count == 5
    assert restarted._turn_bank_pending == turns


def test_version_two_boolean_completed_count_rejected(tmp_path):
    state_path = tmp_path / "turn-bank.json"
    payload = _valid_v2_state(completed=2, pending=2)
    payload["completed_count"] = True
    state_path.write_text(json.dumps(payload), encoding="utf-8")
    restarted = _restarted_agent(tmp_path, state_path)
    hydrate_turn_bank(
        restarted,
        _messages(("first", "answer one"), ("second", "answer two")),
    )

    assert restarted._turn_bank_completed_count == 2
    assert restarted._turn_bank_pending == [
        ("first", "answer one"),
        ("second", "answer two"),
    ]


def test_version_two_negative_count_rejected(tmp_path):
    state_path = tmp_path / "turn-bank.json"
    payload = _valid_v2_state(completed=-1, pending=2)
    state_path.write_text(json.dumps(payload), encoding="utf-8")
    restarted = _restarted_agent(tmp_path, state_path)
    hydrate_turn_bank(
        restarted,
        _messages(("first", "answer one"), ("second", "answer two")),
    )

    assert restarted._turn_bank_completed_count == 2
    assert restarted._turn_bank_pending == [
        ("first", "answer one"),
        ("second", "answer two"),
    ]


def test_version_two_invalid_digest_rejected(tmp_path):
    state_path = tmp_path / "turn-bank.json"
    payload = _valid_v2_state(completed=2, pending=0)
    payload["checkpoint_digest"] = "not-a-hex-digest"
    state_path.write_text(json.dumps(payload), encoding="utf-8")
    restarted = _restarted_agent(tmp_path, state_path)
    hydrate_turn_bank(
        restarted,
        _messages(("first", "answer one"), ("second", "answer two")),
    )

    assert restarted._turn_bank_completed_count == 2
    assert restarted._turn_bank_pending == [
        ("first", "answer one"),
        ("second", "answer two"),
    ]


def test_version_two_non_boolean_write_due_rejected(tmp_path):
    state_path = tmp_path / "turn-bank.json"
    payload = _valid_v2_state(completed=2, pending=0)
    payload["write_due"] = "yes"
    state_path.write_text(json.dumps(payload), encoding="utf-8")
    restarted = _restarted_agent(tmp_path, state_path)
    hydrate_turn_bank(
        restarted,
        _messages(("first", "answer one"), ("second", "answer two")),
    )

    assert restarted._turn_bank_completed_count == 2
    assert restarted._turn_bank_pending == [
        ("first", "answer one"),
        ("second", "answer two"),
    ]


def test_version_two_repeated_text_checkpoint_bound_to_count(tmp_path):
    from agent.turn_bank import _checkpoint_digest, _turn_digest

    state_path = tmp_path / "turn-bank.json"
    repeated = ("same prompt", "same answer")
    payload = _valid_v2_state(completed=2, pending=0)
    turn_digest = _turn_digest(*repeated)
    payload["checkpoint_digest"] = _checkpoint_digest(1, turn_digest)
    state_path.write_text(json.dumps(payload), encoding="utf-8")
    restarted = _restarted_agent(tmp_path, state_path)
    hydrate_turn_bank(restarted, _messages(repeated, repeated, repeated))

    assert restarted._turn_bank_completed_count == 3
    assert restarted._turn_bank_pending == [repeated, repeated, repeated]


def test_version_two_repeated_text_pending_bound_to_base_count(tmp_path):
    from agent.turn_bank import _checkpoint_digest, _pending_digest, _turn_digest

    state_path = tmp_path / "turn-bank.json"
    repeated = ("same prompt", "same answer")
    payload = _valid_v2_state(completed=2, pending=1)
    turn_digest = _turn_digest(*repeated)
    payload["checkpoint_digest"] = _checkpoint_digest(2, turn_digest)
    payload["pending_digest"] = _pending_digest(1, [repeated])
    state_path.write_text(json.dumps(payload), encoding="utf-8")
    restarted = _restarted_agent(tmp_path, state_path)
    hydrate_turn_bank(restarted, _messages(repeated, repeated, repeated))

    assert restarted._turn_bank_completed_count == 3
    assert restarted._turn_bank_pending == [repeated, repeated, repeated]


def test_version_two_pending_exceeds_completed_rejected(tmp_path):
    state_path = tmp_path / "turn-bank.json"
    payload = _valid_v2_state(completed=1, pending=3)
    state_path.write_text(json.dumps(payload), encoding="utf-8")
    restarted = _restarted_agent(tmp_path, state_path)
    hydrate_turn_bank(
        restarted,
        _messages(("first", "answer one"), ("second", "answer two")),
    )

    assert restarted._turn_bank_completed_count == 2
    assert restarted._turn_bank_pending == [
        ("first", "answer one"),
        ("second", "answer two"),
    ]


def test_stale_state_pre_boundary_write_failure_recovers_full_history(tmp_path):
    state_path = tmp_path / "turn-bank.json"
    writer = SimpleNamespace(
        _turn_bank_interval=2,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _turn_bank_state_path=state_path,
        _memory_enabled=True,
        _session_messages=[],
        _memory_store=_Store(),
    )
    assert add_completed_turn(writer, "first", "answer one") is False
    with patch(
        "agent.turn_bank.atomic_replace",
        side_effect=lambda *args, **kwargs: (_ for _ in ()).throw(
            OSError("state write failed")
        ),
    ):
        with patch(
            "tools.memory_tool.memory_tool",
            return_value=json.dumps({"success": True, "staged": True}),
        ):
            assert add_completed_turn(writer, "second", "answer two") is False

    restarted = _restarted_agent(tmp_path, state_path)
    hydrate_turn_bank(
        restarted,
        _messages(("first", "answer one"), ("second", "answer two")),
    )

    assert restarted._turn_bank_completed_count == 2
    assert restarted._turn_bank_pending == [
        ("first", "answer one"),
        ("second", "answer two"),
    ]


def test_stale_state_failed_final_write_recovers_empty_pending(tmp_path):
    from utils import atomic_replace as _real_atomic_replace

    state_path = tmp_path / "turn-bank.json"
    store = _Store()
    store.memory_entries = []
    writer = SimpleNamespace(
        _turn_bank_interval=2,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _turn_bank_state_path=state_path,
        _memory_enabled=True,
        _session_messages=[],
        _memory_store=store,
    )

    def persist(**kwargs):
        kwargs["store"].memory_entries.append(kwargs["content"])
        return json.dumps({"success": True, "staged": False})

    assert add_completed_turn(writer, "first", "answer one") is False
    calls = {"n": 0}

    def flaky_replace(src, dst):
        calls["n"] += 1
        if calls["n"] == 2:
            raise OSError("final state write failed")
        return _real_atomic_replace(src, dst)

    with patch("agent.turn_bank.atomic_replace", side_effect=flaky_replace):
        with patch("tools.memory_tool.memory_tool", side_effect=persist):
            assert add_completed_turn(writer, "second", "answer two") is True

    assert len(store.memory_entries) == 1
    assert "first" in store.memory_entries[0]
    assert "second" in store.memory_entries[0]

    restarted_store = _Store()
    restarted_store.memory_entries = list(store.memory_entries)
    restarted = _restarted_agent(tmp_path, state_path, store=restarted_store)
    hydrate_turn_bank(
        restarted,
        _messages(("first", "answer one"), ("second", "answer two")),
    )

    assert restarted._turn_bank_completed_count == 2
    assert restarted._turn_bank_pending == []

    with patch("tools.memory_tool.memory_tool", side_effect=persist) as write:
        assert add_completed_turn(restarted, "third", "answer three") is False
        assert add_completed_turn(restarted, "fourth", "answer four") is True

    bank_calls = [
        c.kwargs["content"]
        for c in write.call_args_list
        if "Long-term turn bank" in c.kwargs["content"]
    ]
    assert bank_calls
    next_bank = bank_calls[-1]
    assert "third" in next_bank and "fourth" in next_bank
    assert "first" not in next_bank and "second" not in next_bank


def test_stale_state_due_write_failure_restores_write_due(tmp_path):
    from utils import atomic_replace as _real_atomic_replace

    state_path = tmp_path / "turn-bank.json"
    writer_store = _Store()
    writer_store.memory_entries = []
    writer = SimpleNamespace(
        _turn_bank_interval=2,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _turn_bank_state_path=state_path,
        _memory_enabled=True,
        _session_messages=[],
        _memory_store=writer_store,
    )

    def raising_persist(**kwargs):
        raise RuntimeError("memory unavailable")

    assert add_completed_turn(writer, "first", "answer one") is False
    calls = {"n": 0}

    def flaky_replace(src, dst):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError("due state write failed")
        return _real_atomic_replace(src, dst)

    with patch("agent.turn_bank.atomic_replace", side_effect=flaky_replace):
        with patch("tools.memory_tool.memory_tool", side_effect=raising_persist):
            assert add_completed_turn(writer, "second", "answer two") is False

    stale = json.loads(state_path.read_text(encoding="utf-8"))
    assert stale["completed_count"] == 1
    assert stale["pending_count"] == 1
    assert stale["write_due"] is False

    restarted_store = _Store()
    restarted_store.memory_entries = []
    restarted = _restarted_agent(tmp_path, state_path, store=restarted_store)
    hydrate_turn_bank(
        restarted,
        _messages(("first", "answer one"), ("second", "answer two")),
    )

    assert restarted._turn_bank_completed_count == 2
    assert restarted._turn_bank_pending == [
        ("first", "answer one"),
        ("second", "answer two"),
    ]
    assert restarted._turn_bank_write_due is True

    with patch(
        "tools.memory_tool.memory_tool",
        return_value=json.dumps({"success": True, "staged": False}),
    ) as write:
        assert add_completed_turn(restarted, "third", "answer three") is True

    assert write.call_count == 1
    content = write.call_args.kwargs["content"]
    for text in ("first", "second", "third"):
        assert text in content


def test_persisted_prefix_does_not_clear_unproved_repeated_turn():
    store = _Store()
    store.memory_entries = [_format_turn("same", "answer")]
    restarted = SimpleNamespace(
        _turn_bank_interval=2,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _memory_enabled=True,
        _session_messages=[],
        _memory_store=store,
    )
    hydrate_turn_bank(
        restarted,
        _messages(
            ("same", "answer"),
            ("same", "answer"),
        ),
    )

    assert restarted._turn_bank_completed_count == 2
    assert restarted._turn_bank_pending == [("same", "answer")]


def test_persisted_prefix_clears_proved_repeated_turns():
    store = _Store()
    store.memory_entries = [
        _format_turn("same", "answer"),
        _format_turn("same", "answer"),
    ]
    restarted = SimpleNamespace(
        _turn_bank_interval=2,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _memory_enabled=True,
        _session_messages=[],
        _memory_store=store,
    )
    hydrate_turn_bank(
        restarted,
        _messages(
            ("same", "answer"),
            ("same", "answer"),
        ),
    )

    assert restarted._turn_bank_completed_count == 2
    assert restarted._turn_bank_pending == []


def test_absent_checkpoint_blocks_recovery_preserves_history(tmp_path):
    state_path = tmp_path / "turn-bank.json"
    payload = _valid_v2_state(completed=5, pending=5)
    state_path.write_text(json.dumps(payload), encoding="utf-8")
    turns = [("prompt one", "answer one"), ("prompt two", "answer two")]
    restarted = _restarted_agent(tmp_path, state_path)
    hydrate_turn_bank(restarted, _messages(*turns))

    assert restarted._turn_bank_blocked is True
    assert restarted._turn_bank_pending == turns
    with patch("tools.memory_tool.memory_tool") as write:
        assert add_completed_turn(restarted, "third", "answer three") is False
    write.assert_not_called()


def test_memory_reconcile_longer_memory_prefix_clears_more(tmp_path):
    from agent.turn_bank import _bank_body, _checkpoint_digest, _pending_digest, _turn_digest

    turns = [
        ("first", "answer one"),
        ("second", "answer two"),
        ("third", "answer three"),
    ]
    state_path = tmp_path / "turn-bank.json"
    payload = _valid_v2_state(completed=2, pending=2)
    payload["checkpoint_digest"] = _checkpoint_digest(
        2, _turn_digest(*turns[1])
    )
    payload["pending_digest"] = _pending_digest(2, turns[:2])
    state_path.write_text(json.dumps(payload), encoding="utf-8")
    store = _Store()
    store.memory_entries = [
        f"[Long-term turn bank — 3 completed turns]\n\n{_bank_body(turns)}"
    ]
    restarted = _restarted_agent(tmp_path, state_path, store=store)
    hydrate_turn_bank(restarted, _messages(*turns))

    assert restarted._turn_bank_completed_count == 3
    assert restarted._turn_bank_pending == []


def test_state_write_failure_retries_pending_once(agent):
    staged = json.dumps({"success": True, "staged": True})
    successful = json.dumps({"success": True, "staged": False})
    with patch("tools.memory_tool.memory_tool") as write:
        write.side_effect = [staged, successful]
        assert add_completed_turn(agent, "first", "answer one") is False
        assert add_completed_turn(agent, "second", "answer two") is False
        assert add_completed_turn(agent, "third", "answer three") is True

    assert write.call_count == 2
    content = write.call_args.kwargs["content"]
    for text in ("first", "second", "third"):
        assert text in content
    assert agent._turn_bank_pending == []
    assert agent._turn_bank_completed_count == 3


def test_resume_tail_full_history_recovers_pending_via_bounded_read(tmp_path):
    from agent.turn_bank import _checkpoint_digest, _pending_digest, _turn_digest

    turns = [(f"prompt {i:02d}", f"answer {i:02d}") for i in range(1, 26)]
    state_path = tmp_path / "turn-bank.json"
    payload = _valid_v2_state(completed=25, pending=25)
    payload["checkpoint_digest"] = _checkpoint_digest(25, _turn_digest(*turns[-1]))
    payload["pending_digest"] = _pending_digest(25, turns)
    state_path.write_text(json.dumps(payload), encoding="utf-8")
    session_db = _SessionWithConn(_desc_rows(_messages(*turns)))
    restarted = SimpleNamespace(
        _turn_bank_interval=2,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _turn_bank_state_path=state_path,
        _memory_enabled=True,
        _session_messages=[],
        _memory_store=_Store(),
        _session_db=session_db,
        session_id="sess",
    )
    hydrate_turn_bank(restarted, _messages(*turns[5:]))

    assert restarted._turn_bank_pending == turns
    assert restarted._turn_bank_completed_count == 25
    assert session_db._conn.calls


def _sidecar_file(dir, session_id):
    digest = hashlib.sha256(str(session_id).encode("utf-8")).hexdigest()[:24]
    return dir / f".turn_bank_{digest}.json"


class _LineageSession:
    def __init__(self, rows, records):
        self._conn = _RecordConn(rows)
        self._records = records

    def get_session(self, session_id):
        return self._records.get(session_id)


def test_compression_lineage_restores_ancestor_turns(tmp_path):
    from agent.turn_bank import _checkpoint_digest, _pending_digest, _turn_digest

    root_sid = "root-session"
    child_sid = "child-session"
    turns = [("root one", "root answer"), ("child two", "child answer")]
    payload = _valid_v2_state(completed=2, pending=2)
    payload["checkpoint_digest"] = _checkpoint_digest(2, _turn_digest(*turns[-1]))
    payload["pending_digest"] = _pending_digest(2, turns)
    _sidecar_file(tmp_path, root_sid).write_text(json.dumps(payload), encoding="utf-8")
    records = {
        root_sid: {
            "id": root_sid,
            "end_reason": "compression",
            "ended_at": 100,
            "parent_session_id": None,
        },
        child_sid: {
            "id": child_sid,
            "started_at": 200,
            "end_reason": None,
            "ended_at": None,
            "parent_session_id": root_sid,
        },
    }
    session_db = _LineageSession(_desc_rows(_messages(*turns)), records)
    restarted = _restarted_agent(tmp_path, tmp_path / "child-bank.json")
    restarted.session_id = child_sid
    restarted._parent_session_id = root_sid
    restarted._session_db = session_db
    hydrate_turn_bank(restarted, _messages(turns[-1]))

    assert restarted._turn_bank_completed_count == 2
    assert restarted._turn_bank_pending == turns


def test_false_compression_parent_uses_safe_history_recovery(tmp_path):
    from agent.turn_bank import _checkpoint_digest, _pending_digest, _turn_digest

    parent_sid = "parent-session"
    child_sid = "child-session"
    turns = [("first", "answer one"), ("second", "answer two")]
    parent_turns = [
        ("p one", "p answer one"),
        ("p two", "p answer two"),
        ("p three", "p answer three"),
    ]
    payload = _valid_v2_state(completed=3, pending=3)
    payload["checkpoint_digest"] = _checkpoint_digest(3, _turn_digest(*parent_turns[-1]))
    payload["pending_digest"] = _pending_digest(3, parent_turns)
    _sidecar_file(tmp_path, parent_sid).write_text(
        json.dumps(payload), encoding="utf-8"
    )
    records = {
        parent_sid: {
            "id": parent_sid,
            "end_reason": "compression",
            "ended_at": 200,
            "parent_session_id": None,
        },
        child_sid: {
            "id": child_sid,
            "started_at": 100,
            "end_reason": None,
            "ended_at": None,
            "parent_session_id": parent_sid,
        },
    }
    session_db = _LineageSession(_desc_rows(_messages(*turns)), records)
    restarted = _restarted_agent(tmp_path, tmp_path / "child-bank.json")
    restarted.session_id = child_sid
    restarted._parent_session_id = parent_sid
    restarted._session_db = session_db
    hydrate_turn_bank(restarted, _messages(*turns))

    assert getattr(restarted, "_turn_bank_blocked", False) is False
    assert restarted._turn_bank_completed_count == 2
    assert restarted._turn_bank_pending == turns


def test_chained_compression_prefers_nearest_ancestor_sidecar(tmp_path):
    from agent.turn_bank import _checkpoint_digest, _pending_digest, _turn_digest

    root_sid = "root-session"
    middle_sid = "middle-session"
    child_sid = "child-session"
    turns = [(f"turn {i}", f"answer {i}") for i in range(1, 5)]
    root_payload = _valid_v2_state(completed=2, pending=2)
    root_payload["checkpoint_digest"] = _checkpoint_digest(2, _turn_digest(*turns[-1]))
    root_payload["pending_digest"] = _pending_digest(2, turns[:2])
    _sidecar_file(tmp_path, root_sid).write_text(
        json.dumps(root_payload), encoding="utf-8"
    )
    middle_payload = _valid_v2_state(completed=4, pending=3)
    middle_payload["checkpoint_digest"] = _checkpoint_digest(
        4, _turn_digest(*turns[-1])
    )
    middle_payload["pending_digest"] = _pending_digest(4, turns[1:])
    _sidecar_file(tmp_path, middle_sid).write_text(
        json.dumps(middle_payload), encoding="utf-8"
    )
    records = {
        root_sid: {
            "id": root_sid,
            "end_reason": "compression",
            "ended_at": 50,
            "parent_session_id": None,
        },
        middle_sid: {
            "id": middle_sid,
            "end_reason": "compression",
            "ended_at": 100,
            "started_at": 80,
            "parent_session_id": root_sid,
        },
        child_sid: {
            "id": child_sid,
            "started_at": 200,
            "end_reason": None,
            "ended_at": None,
            "parent_session_id": middle_sid,
        },
    }
    session_db = _LineageSession(_desc_rows(_messages(*turns)), records)
    restarted = _restarted_agent(tmp_path, tmp_path / "child-bank.json")
    restarted.session_id = child_sid
    restarted._parent_session_id = middle_sid
    restarted._session_db = session_db
    hydrate_turn_bank(restarted, _messages(turns[-1]))

    assert restarted._turn_bank_completed_count == 4
    assert restarted._turn_bank_pending == turns[1:]


def test_branch_isolation_ignores_parent_state_and_copied_turns(tmp_path):
    from agent.turn_bank import _checkpoint_digest, _pending_digest, _turn_digest

    parent_sid = "parent-session"
    child_sid = "child-session"
    parent_turns = [("p one", "p answer one"), ("p two", "p answer two")]
    payload = _valid_v2_state(completed=2, pending=2)
    payload["checkpoint_digest"] = _checkpoint_digest(2, _turn_digest(*parent_turns[-1]))
    payload["pending_digest"] = _pending_digest(2, parent_turns)
    _sidecar_file(tmp_path, parent_sid).write_text(
        json.dumps(payload), encoding="utf-8"
    )
    records = {
        parent_sid: {
            "id": parent_sid,
            "end_reason": "branched",
            "ended_at": 100,
            "parent_session_id": None,
        },
        child_sid: {
            "id": child_sid,
            "started_at": 200,
            "end_reason": None,
            "ended_at": None,
            "parent_session_id": parent_sid,
        },
    }
    session_db = _LineageSession(_desc_rows(_messages(*parent_turns)), records)
    restarted = _restarted_agent(tmp_path, tmp_path / "child-bank.json")
    restarted.session_id = child_sid
    restarted._parent_session_id = parent_sid
    restarted._session_db = session_db
    hydrate_turn_bank(restarted, _messages(*parent_turns))

    assert restarted._turn_bank_completed_count == 0
    assert restarted._turn_bank_pending == []


def test_branch_resumed_tail_copied_suffix_adds_no_child_turns(tmp_path):
    from agent.turn_bank import _checkpoint_digest, _pending_digest, _turn_digest

    parent_sid = "parent-session"
    child_sid = "child-session"
    parent_turns = [(f"prompt {i:02d}", f"answer {i:02d}") for i in range(1, 31)]
    child_turns = parent_turns[10:] + [("brand new", "brand answer")]
    payload = _valid_v2_state(completed=30, pending=30)
    payload["checkpoint_digest"] = _checkpoint_digest(
        30, _turn_digest(*parent_turns[-1])
    )
    payload["pending_digest"] = _pending_digest(30, parent_turns)
    _sidecar_file(tmp_path, parent_sid).write_text(
        json.dumps(payload), encoding="utf-8"
    )
    records = {
        parent_sid: {
            "id": parent_sid,
            "end_reason": "branched",
            "ended_at": 100,
            "parent_session_id": None,
        },
        child_sid: {
            "id": child_sid,
            "started_at": 200,
            "end_reason": None,
            "ended_at": None,
            "parent_session_id": parent_sid,
        },
    }
    session_db = _LineageSession(_desc_rows(_messages(*parent_turns)), records)
    restarted = _restarted_agent(tmp_path, tmp_path / "child-bank.json")
    restarted.session_id = child_sid
    restarted._parent_session_id = parent_sid
    restarted._session_db = session_db
    hydrate_turn_bank(restarted, _messages(*child_turns))

    assert restarted._turn_bank_completed_count == 1
    assert restarted._turn_bank_pending == [("brand new", "brand answer")]


def test_branch_ambiguous_boundary_blocks_memory_writes(tmp_path):
    parent_sid = "parent-session"
    child_sid = "child-session"
    repeated = ("same prompt", "same answer")
    parent_turns = [repeated, repeated]
    child_turns = [repeated, repeated, ("brand new", "brand answer")]
    records = {
        parent_sid: {
            "id": parent_sid,
            "end_reason": "branched",
            "ended_at": 100,
            "parent_session_id": None,
        },
        child_sid: {
            "id": child_sid,
            "started_at": 200,
            "end_reason": None,
            "ended_at": None,
            "parent_session_id": parent_sid,
        },
    }
    session_db = _LineageSession(_desc_rows(_messages(*parent_turns)), records)
    restarted = _restarted_agent(tmp_path, tmp_path / "child-bank.json")
    restarted.session_id = child_sid
    restarted._parent_session_id = parent_sid
    restarted._session_db = session_db
    hydrate_turn_bank(restarted, _messages(*child_turns))

    assert restarted._turn_bank_blocked is True

    with patch("tools.memory_tool.memory_tool") as write:
        assert add_completed_turn(restarted, "extra", "extra answer") is False
        write.assert_not_called()


def test_blocked_history_keeps_unproved_turn_without_memory_call(tmp_path):
    state_path = tmp_path / "turn-bank.json"
    payload = _valid_v2_state(completed=5, pending=5)
    state_path.write_text(json.dumps(payload), encoding="utf-8")
    turns = [("prompt one", "answer one"), ("prompt two", "answer two")]
    restarted = _restarted_agent(tmp_path, state_path)
    restarted.session_id = "sess"
    restarted._session_db = SimpleNamespace(_conn=_RaiseConn())
    hydrate_turn_bank(restarted, _messages(*turns))

    assert restarted._turn_bank_blocked is True

    before = state_path.read_bytes()
    with patch("tools.memory_tool.memory_tool") as write:
        assert add_completed_turn(restarted, "third", "answer three") is False
        write.assert_not_called()

    assert state_path.read_bytes() == before
    assert ("third", "answer three") in restarted._turn_bank_pending


def test_session_isolation_clears_bank_on_session_change(tmp_path):
    agent = SimpleNamespace(
        _turn_bank_interval=2,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _turn_bank_state_path=tmp_path / "turn-bank.json",
        _memory_enabled=True,
        _memory_store=_Store(),
        _session_messages=[],
        session_id="old",
    )
    with patch("tools.memory_tool.memory_tool") as write:
        write.return_value = json.dumps({"success": True, "staged": False})
        assert add_completed_turn(agent, "first", "answer one") is False

        agent.session_id = "new"
        assert add_completed_turn(agent, "second", "answer two") is False

    content = write.call_args.kwargs["content"] if write.call_count else ""
    assert "first" not in content
    assert agent._turn_bank_completed_count == 1
    assert agent._turn_bank_pending == [("second", "answer two")]


def test_compression_continuation_preserves_pending_bank(tmp_path):
    agent = SimpleNamespace(
        _turn_bank_interval=2,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _turn_bank_state_path=tmp_path / "turn-bank.json",
        _memory_enabled=True,
        _memory_store=_Store(),
        _session_messages=[],
        session_id="parent",
    )
    with patch("tools.memory_tool.memory_tool") as write:
        write.return_value = json.dumps({"success": True, "staged": False})
        assert add_completed_turn(agent, "first", "answer one") is False

        agent.session_id = "child"
        agent._parent_session_id = "parent"
        agent._session_db = SimpleNamespace(
            get_session=lambda sid: {
                "parent": {"end_reason": "compression", "ended_at": 100},
                "child": {"started_at": 200, "parent_session_id": "parent"},
            }.get(sid)
        )
        assert add_completed_turn(agent, "second", "answer two") is True

    write.assert_called_once()
    content = write.call_args.kwargs["content"]
    assert "first" in content
    assert "second" in content
    assert agent._turn_bank_completed_count == 2
    assert agent._turn_bank_pending == []


def test_normal_pending_cadence_writes_only_at_boundary(tmp_path):
    agent = SimpleNamespace(
        _turn_bank_interval=4,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _turn_bank_state_path=tmp_path / "turn-bank.json",
        _memory_enabled=True,
        _memory_store=_Store(),
        _session_messages=[],
        session_id="sess",
    )
    with patch("tools.memory_tool.memory_tool") as write:
        write.return_value = json.dumps({"success": True, "staged": False})
        for i in range(1, 4):
            assert add_completed_turn(agent, f"turn {i}", f"answer {i}") is False
            assert write.call_count == 0
            assert agent._turn_bank_write_due is False

        assert add_completed_turn(agent, "turn 4", "answer 4") is True

    assert write.call_count == 1
    content = write.call_args.kwargs["content"]
    for i in range(1, 5):
        assert f"turn {i}" in content


def test_repeated_retry_writes_on_each_completed_turn(tmp_path):
    agent = SimpleNamespace(
        _turn_bank_interval=2,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _turn_bank_state_path=tmp_path / "turn-bank.json",
        _memory_enabled=True,
        _memory_store=_Store(),
        _session_messages=[],
        session_id="sess",
    )
    successful = json.dumps({"success": True, "staged": False})
    with patch("tools.memory_tool.memory_tool") as write:
        write.side_effect = [
            RuntimeError("memory write failed"),
            RuntimeError("memory write failed"),
            successful,
        ]
        assert add_completed_turn(agent, "first", "answer one") is False
        assert add_completed_turn(agent, "second", "answer two") is False
        assert add_completed_turn(agent, "third", "answer three") is False
        assert add_completed_turn(agent, "fourth", "answer four") is True

    assert write.call_count == 3
    content = write.call_args.kwargs["content"]
    for text in ("first", "second", "third", "fourth"):
        assert text in content
    assert agent._turn_bank_pending == []
    assert agent._turn_bank_completed_count == 4


def test_canonical_transcript_prefers_persisted_pair_over_transformed_text(tmp_path):
    state_path = tmp_path / "turn-bank.json"
    agent = SimpleNamespace(
        _turn_bank_interval=1,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _turn_bank_state_path=state_path,
        _memory_enabled=True,
        _session_messages=_messages(("request", "raw answer")),
        _memory_store=_Store(),
        _memory_manager=None,
    )
    with patch("tools.memory_tool.memory_tool") as write:
        write.return_value = json.dumps({"success": True, "staged": False})
        assert add_completed_turn(agent, "request", "DISPLAY answer") is True

    content = write.call_args.kwargs["content"]
    assert "raw answer" in content
    assert "DISPLAY answer" not in content
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["checkpoint_digest"] == _checkpoint_digest(
        1, _turn_digest("request", "raw answer")
    )


def test_canonical_transcript_uses_latest_occurrence_for_identical_user_text(tmp_path):
    agent = SimpleNamespace(
        _turn_bank_interval=1,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _turn_bank_state_path=tmp_path / "turn-bank.json",
        _memory_enabled=True,
        _session_messages=_messages(
            ("repeat", "first raw"),
            ("repeat", "second raw"),
        ),
        _memory_store=_Store(),
        _memory_manager=None,
    )
    with patch("tools.memory_tool.memory_tool") as write:
        write.return_value = json.dumps({"success": True, "staged": False})
        assert add_completed_turn(agent, "repeat", "whatever display") is True

    content = write.call_args.kwargs["content"]
    assert "second raw" in content
    assert "first raw" not in content


class _BankStore:
    memory_char_limit = 100_000
    user_char_limit = 100_000

    def __init__(self):
        self.memory_entries = []
        self.user_entries = []

    def _char_count(self, target):
        entries = self.memory_entries if target == "memory" else self.user_entries
        return len("\n\n".join(entries))

    def add(self, target, content):
        entries = self.memory_entries if target == "memory" else self.user_entries
        entries.append(content)
        return {"success": True}


def test_production_loop_banks_raw_not_display_text(tmp_path, monkeypatch):
    from unittest.mock import MagicMock

    import run_agent as run_agent_module
    from run_agent import AIAgent

    xavani_home = tmp_path / ".xavani"
    xavani_home.mkdir()
    monkeypatch.setenv("XAVANI_HOME", str(xavani_home))

    message = SimpleNamespace(content="raw answer", tool_calls=None)
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=message, finish_reason="stop")],
        model="test/model",
        usage=None,
    )

    def _fake_invoke_hook(hook_name, **kwargs):
        if hook_name == "transform_llm_output":
            return ["display answer"]
        return []

    with (
        patch("run_agent.get_tool_definitions", return_value=[]),
        patch("run_agent.check_toolset_requirements", return_value={}),
        patch("run_agent.OpenAI"),
        patch("xavani_cli.plugins.invoke_hook", side_effect=_fake_invoke_hook),
    ):
        agent = AIAgent(
            api_key="test-key-1234567890",
            base_url="https://openrouter.ai/api/v1",
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
        )
        agent.client = MagicMock()
        agent.client.chat.completions.create.return_value = response
        agent._cached_system_prompt = "You are helpful."
        agent._use_prompt_caching = False
        agent.tool_delay = 0
        agent.compression_enabled = False
        agent.save_trajectories = False
        agent.suppress_status_output = True
        agent._print_fn = lambda *args, **kw: None

        store = _BankStore()
        agent._memory_enabled = True
        agent._memory_store = store
        agent._turn_bank_state_path = tmp_path / "turn-bank.json"
        agent._turn_bank_interval = 1

        with (
            patch.object(agent, "_save_session_log"),
            patch.object(agent, "_flush_messages_to_session_db_unlocked"),
            patch.object(agent, "_save_trajectory"),
            patch.object(agent, "_cleanup_task_resources"),
        ):
            result = agent.run_conversation("request")

    assert result["final_response"] == "display answer"
    assert any(
        isinstance(m, dict)
        and m.get("role") == "assistant"
        and m.get("content") == "raw answer"
        for m in agent._session_messages
    )
    bank_entries = [
        e for e in store.memory_entries if e.startswith("[Long-term turn bank")
    ]
    assert len(bank_entries) == 1
    banked = bank_entries[0]
    assert "raw answer" in banked
    assert "display answer" not in banked


def _bank_entry(count: int, turns) -> str:
    body = "\n\n".join(_format_turn(user, assistant) for user, assistant in turns)
    return f"[Long-term turn bank — {count} completed turns]\n\n{body}"


def _store_with(entry: str):
    store = _Store()
    store.memory_entries = [entry]
    return store


def test_whole_bank_header_count_proves_prefix():
    turns = [("first", "answer one"), ("second", "answer two")]
    store = _store_with(_bank_entry(2, turns))
    assert _persisted_prefix_length(turns, 2, store) == 2


def test_whole_bank_mismatched_header_count_rejects_prefix():
    turns = [("first", "answer one"), ("second", "answer two")]
    store = _store_with(_bank_entry(3, turns))
    assert _persisted_prefix_length(turns, 2, store) == 0


def test_whole_bank_nonzero_base_header_proves_prefix():
    history = [
        ("t1", "a1"),
        ("t2", "a2"),
        ("t3", "a3"),
        ("t4", "a4"),
        ("t5", "a5"),
        ("t6", "a6"),
    ]
    candidate = history[4:]
    store = _store_with(_bank_entry(6, candidate))
    assert _persisted_prefix_length(candidate, 2, store, base_count=4) == 2


def test_whole_bank_wrong_base_header_rejects_prefix():
    history = [
        ("t1", "a1"),
        ("t2", "a2"),
        ("t3", "a3"),
        ("t4", "a4"),
        ("t5", "a5"),
        ("t6", "a6"),
    ]
    candidate = history[4:]
    store = _store_with(_bank_entry(2, candidate))
    assert _persisted_prefix_length(candidate, 2, store, base_count=4) == 0


def test_repeated_retry_interval_four_writes_on_each_completed_turn(agent):
    agent._turn_bank_interval = 4
    with patch("tools.memory_tool.memory_tool") as write:
        write.side_effect = [
            RuntimeError("fail one"),
            RuntimeError("fail two"),
            json.dumps({"success": True, "staged": False}),
        ]
        assert add_completed_turn(agent, "first", "answer one") is False
        assert add_completed_turn(agent, "second", "answer two") is False
        assert add_completed_turn(agent, "third", "answer three") is False
        assert add_completed_turn(agent, "fourth", "answer four") is False
        assert add_completed_turn(agent, "fifth", "answer five") is False
        assert add_completed_turn(agent, "sixth", "answer six") is True
    assert write.call_count == 3
    banked = write.call_args.kwargs["content"]
    for text in ("first", "second", "third", "fourth", "fifth", "sixth"):
        assert text in banked
    assert agent._turn_bank_pending == []


def test_unmatched_latest_request_with_nonempty_args_banks_nothing(agent):
    agent._turn_bank_interval = 1
    agent._session_messages = [
        {"role": "user", "content": "same question"},
        {"role": "assistant", "content": "earlier answer"},
        {"role": "user", "content": "same question"},
    ]
    with patch("tools.memory_tool.memory_tool") as write:
        assert add_completed_turn(agent, "same question", "display text") is False
    write.assert_not_called()
    assert len(agent._memory_store.memory_entries) == 0
