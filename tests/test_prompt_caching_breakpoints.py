# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Task 7 — cache-control breakpoints on tools + stable history prefix.

End-to-end (no live API) assertions on the real request builder:

- api_mode ``anthropic_messages`` requests carry ``cache_control`` on the
  tools block (breakpoint 1), the system prompt block (breakpoint 2) and the
  last message of the stable history prefix — the oldest-kept boundary
  (breakpoint 3). Total never exceeds 4 breakpoints.
- The system prompt and tool schema list stay byte-stable across turns.
- Non-Anthropic paths carry no ``cache_control`` fields at all.
"""

import copy
import json

import pytest

from agent.anthropic_adapter import (
    build_anthropic_kwargs,
    convert_tools_to_anthropic,
)
from agent.prompt_caching import apply_anthropic_cache_control

MARKER = {"type": "ephemeral"}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web",
            "parameters": {
                "type": "object",
                "properties": {"q": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file from disk",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
            },
        },
    },
]

SYSTEM_PROMPT = "You are Xavani Agent. Be concise and correct."


def _history_messages(n_history: int, system: str = SYSTEM_PROMPT) -> list:
    """Build OpenAI-style messages the way conversation_loop does."""
    msgs = [{"role": "system", "content": system}]
    for i in range(n_history):
        role = "user" if i % 2 == 0 else "assistant"
        msgs.append({"role": role, "content": f"msg{i}"})
    return msgs


def _build_anthropic_payload(
    messages: list,
    tools=None,
    *,
    cache_control: bool = True,
    history_breakpoints: int = 1,
    cache_ttl: str = "5m",
    session_id: str = None,
) -> dict:
    """Run the real production pipeline: message markers → adapter kwargs."""
    if cache_control:
        messages = apply_anthropic_cache_control(
            messages,
            cache_ttl=cache_ttl,
            native_anthropic=True,
            history_breakpoints=history_breakpoints,
        )
    return build_anthropic_kwargs(
        model="claude-sonnet-4-6",
        messages=messages,
        tools=tools,
        max_tokens=4096,
        reasoning_config=None,
        cache_control=cache_control,
        cache_ttl=cache_ttl,
        session_id=session_id,
    )


def _count_cache_control(obj) -> int:
    """Count cache_control markers anywhere in a payload."""
    if isinstance(obj, dict):
        return (1 if "cache_control" in obj else 0) + sum(
            _count_cache_control(v) for v in obj.values()
        )
    if isinstance(obj, list):
        return sum(_count_cache_control(v) for v in obj)
    return 0


class TestToolsBlockBreakpoint:
    def test_last_tool_carries_cache_control(self):
        kwargs = _build_anthropic_payload(_history_messages(2), tools=TOOLS)
        assert "tools" in kwargs
        assert kwargs["tools"][-1]["cache_control"] == MARKER

    def test_only_last_tool_is_marked(self):
        kwargs = _build_anthropic_payload(_history_messages(2), tools=TOOLS)
        for tool in kwargs["tools"][:-1]:
            assert "cache_control" not in tool

    def test_existing_tool_marker_is_not_doubled(self):
        tools = copy.deepcopy(TOOLS)
        tools[-1]["cache_control"] = {"type": "ephemeral"}
        kwargs = _build_anthropic_payload(_history_messages(2), tools=tools)
        # Exactly one marker on the tools array (the forwarded one) — the
        # builder must not add a second breakpoint on the same block.
        tool_markers = [
            t["cache_control"]
            for t in kwargs["tools"]
            if isinstance(t.get("cache_control"), dict)
        ]
        assert len(tool_markers) == 1
        assert tool_markers[0] == MARKER

    def test_no_tools_no_tools_marker(self):
        kwargs = _build_anthropic_payload(_history_messages(2), tools=None)
        assert "tools" not in kwargs


class TestSystemBlockBreakpoint:
    def test_system_block_carries_cache_control(self):
        kwargs = _build_anthropic_payload(_history_messages(2), tools=TOOLS)
        system = kwargs["system"]
        assert isinstance(system, list)
        marked = [
            b for b in system if isinstance(b, dict) and b.get("cache_control") == MARKER
        ]
        assert len(marked) == 1

    def test_system_marker_appears_exactly_once(self):
        kwargs = _build_anthropic_payload(_history_messages(2), tools=TOOLS)
        assert _count_cache_control(kwargs["system"]) == 1

    def test_system_text_is_byte_stable(self):
        """System prompt string round-trips byte-for-byte (cache-key stability)."""
        kwargs = _build_anthropic_payload(_history_messages(2), tools=TOOLS)
        system = kwargs["system"]
        texts = [b["text"] for b in system if b.get("type") == "text"]
        assert texts == [SYSTEM_PROMPT]


class TestHistoryBoundaryBreakpoint:
    def test_last_message_of_stable_prefix_is_marked(self):
        """history_breakpoints=1 marks only the newest message (the boundary)."""
        kwargs = _build_anthropic_payload(
            _history_messages(6), tools=TOOLS, history_breakpoints=1
        )
        last = kwargs["messages"][-1]
        assert _count_cache_control(last) == 1

    def test_older_history_is_not_marked(self):
        kwargs = _build_anthropic_payload(
            _history_messages(6), tools=TOOLS, history_breakpoints=1
        )
        for msg in kwargs["messages"][:-1]:
            assert _count_cache_control(msg) == 0

    def test_default_history_breakpoints_still_three(self):
        """Default (non-anthropic-messages) strategy keeps system + last 3."""
        msgs = _history_messages(6)
        marked = apply_anthropic_cache_control(
            msgs, native_anthropic=True, history_breakpoints=3
        )
        # System + last 3 non-system = 4 message-level breakpoints.
        assert _count_cache_control(marked) == 4


class TestMaxFourBreakpoints:
    def test_total_breakpoints_within_limit(self):
        kwargs = _build_anthropic_payload(
            _history_messages(6), tools=TOOLS, history_breakpoints=1
        )
        # tools(1) + system(1) + boundary(1) = 3 ≤ 4
        assert _count_cache_control(kwargs) == 3
        assert _count_cache_control(kwargs) <= 4

    def test_message_level_markers_never_exceed_four(self):
        """apply_anthropic_cache_control hard-caps message breakpoints at 4,
        no matter how many history slots are requested."""
        for slots in (3, 5, 20):
            msgs = _history_messages(6)
            marked = apply_anthropic_cache_control(
                msgs, native_anthropic=True, history_breakpoints=slots
            )
            assert _count_cache_control(marked) <= 4

    def test_production_anthropic_payload_is_within_limit(self):
        """tools(1) + system(1) + boundary(1) = 3 ≤ Anthropic's 4 limit."""
        kwargs = _build_anthropic_payload(
            _history_messages(6), tools=TOOLS, history_breakpoints=1
        )
        assert _count_cache_control(kwargs) <= 4


class TestNoCacheControlOffPath:
    def test_builder_default_carries_no_cache_control(self):
        """cache_control=False (non-caching providers) → zero markers."""
        kwargs = _build_anthropic_payload(
            _history_messages(2), tools=TOOLS, cache_control=False
        )
        assert _count_cache_control(kwargs) == 0

    def test_unmarked_messages_stay_clean_when_tools_marked(self):
        """Tools-only marker: message history keeps no cache_control fields."""
        msgs = _history_messages(2)  # no apply_anthropic_cache_control
        kwargs = build_anthropic_kwargs(
            model="claude-sonnet-4-6",
            messages=msgs,
            tools=TOOLS,
            max_tokens=4096,
            reasoning_config=None,
            cache_control=True,
        )
        assert _count_cache_control(kwargs["tools"]) == 1
        assert _count_cache_control(kwargs["messages"]) == 0


class TestByteStability:
    def test_tool_conversion_is_deterministic(self):
        first = convert_tools_to_anthropic(TOOLS)
        second = convert_tools_to_anthropic(TOOLS)
        assert json.dumps(first, sort_keys=True) == json.dumps(
            second, sort_keys=True
        )

    def test_tool_conversion_preserves_input_order(self):
        """Upstream registry supplies sorted-by-name order; adapter keeps it."""
        converted = convert_tools_to_anthropic(TOOLS)
        assert [t["name"] for t in converted] == ["web_search", "read_file"]

    def test_system_rebuilt_identically_when_inputs_unchanged(self):
        a = _build_anthropic_payload(_history_messages(3), tools=TOOLS)
        b = _build_anthropic_payload(_history_messages(3), tools=TOOLS)
        assert json.dumps(a["system"], sort_keys=True) == json.dumps(
            b["system"], sort_keys=True
        )


class TestSessionIdPassthrough:
    def test_session_id_accepted_without_crashing(self):
        """Anthropic's cache keys are content-addressed (no session id field);
        the param is plumbed through the transport chain as a future-proof
        passthrough and must not alter the payload."""
        kwargs = _build_anthropic_payload(
            _history_messages(2), tools=TOOLS, session_id="sess-abc-123"
        )
        assert kwargs["tools"][-1]["cache_control"] == MARKER
        assert kwargs["system"]  # still builds a valid payload
