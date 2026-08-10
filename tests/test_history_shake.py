# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for agent/history_shake.py — the mechanical pre-compaction shake pass.

The shake is a free token-reduction pre-pass that runs BEFORE the LLM
compaction summary is paid for. It is pure, deterministic, and never
calls an LLM. Only tool-result content is eligible for modification.
"""

import copy

from agent.history_shake import shake


def _msg(role, content, **extra):
    m = {"role": role, "content": content}
    m.update(extra)
    return m


# ---------------------------------------------------------------------------
# Consecutive identical tool outputs collapse
# ---------------------------------------------------------------------------


def test_collapses_consecutive_identical_tool_outputs():
    messages = [
        _msg("user", "run the tests"),
        _msg("tool", "3 passed, 0 failed"),
        _msg("tool", "3 passed, 0 failed"),
        _msg("tool", "3 passed, 0 failed"),
        _msg("assistant", "done"),
    ]
    out = shake(messages)
    tool_msgs = [m for m in out if m["role"] == "tool"]
    assert len(out) == 3
    assert len(tool_msgs) == 1
    assert tool_msgs[0]["content"] == "3 passed, 0 failed\n(repeated 3x)"


def test_collapse_ignores_whitespace_differences():
    messages = [
        _msg("tool", "line1\n\n   line2  \n"),
        _msg("tool", "line1 line2"),
    ]
    out = shake(messages)
    assert len(out) == 1
    # The kept message is the LAST occurrence of the run, marker appended.
    assert out[0]["content"] == "line1 line2\n(repeated 2x)"


def test_non_consecutive_identical_outputs_not_collapsed():
    messages = [
        _msg("tool", "same"),
        _msg("user", "hi"),
        _msg("tool", "same"),
    ]
    out = shake(messages)
    assert len(out) == 3
    assert [m["content"] for m in out if m["role"] == "tool"] == ["same", "same"]


def test_single_tool_message_untouched():
    messages = [_msg("tool", "unique output")]
    out = shake(messages)
    assert out == messages
    assert out[0]["content"] == "unique output"


def test_non_string_tool_content_left_alone():
    # Multimodal (list) tool content is not a string — not eligible for
    # whitespace normalization or collapse. Conservatively untouched.
    messages = [
        _msg("tool", [{"type": "text", "text": "a"}], tool_call_id="c1"),
        _msg("tool", [{"type": "text", "text": "a"}], tool_call_id="c2"),
    ]
    out = shake(messages)
    assert len(out) == 2


# ---------------------------------------------------------------------------
# User / assistant text must never change
# ---------------------------------------------------------------------------


def test_user_and_assistant_text_byte_identical():
    messages = [
        _msg("user", "refactor the auth module"),
        _msg("tool", "ok"),
        _msg("tool", "ok"),
        _msg("assistant", "I refactored it:\n```python\nx = 1\n```"),
        _msg("user", "thanks"),
    ]
    out = shake(messages)
    orig_seq = [m for m in messages if m["role"] in ("user", "assistant")]
    out_seq = [m for m in out if m["role"] in ("user", "assistant")]
    assert len(orig_seq) == len(out_seq)
    for original, shaken in zip(orig_seq, out_seq):
        # Same object identity -> content trivially byte-identical.
        assert shaken is original


# ---------------------------------------------------------------------------
# ASCII banner / decorative separator removal
# ---------------------------------------------------------------------------


def test_banner_lines_removed_when_3_plus_occurrences():
    banner = "=" * 40
    messages = [
        _msg("user", "go"),
        _msg("tool", f"output one\n{banner}\nvalue A"),
        _msg("tool", f"output two\n{banner}\nvalue B"),
        _msg("tool", f"output three\n{banner}\nvalue C"),
        _msg("assistant", "done"),
    ]
    out = shake(messages)
    for m in out:
        if m["role"] == "tool":
            assert banner not in m["content"]
    # Content around the banner is preserved.
    tool_contents = [m["content"] for m in out if m["role"] == "tool"]
    assert all("value" in c for c in tool_contents)


def test_banner_under_three_occurrences_kept():
    banner = "-" * 30
    messages = [
        _msg("tool", f"{banner}\nA"),
        _msg("tool", f"{banner}\nB"),
    ]
    out = shake(messages)
    assert out[0]["content"] == f"{banner}\nA"
    assert out[1]["content"] == f"{banner}\nB"


def test_user_message_banners_do_not_count_toward_removal():
    # Only tool-result banners count toward the 3+ removal threshold. A
    # banner in a user message is decoration the shake must not touch, so
    # 1 user occurrence + 2 tool occurrences stays below the threshold and
    # the banner survives in every tool result.
    banner = "=" * 40
    messages = [
        _msg("user", f"{banner}\nplease format this"),
        _msg("tool", f"{banner}\nA"),
        _msg("tool", f"{banner}\nB"),
    ]
    out = shake(messages)
    assert out[0]["content"] == f"{banner}\nplease format this"
    assert out[1]["content"] == f"{banner}\nA"
    assert out[2]["content"] == f"{banner}\nB"


def test_short_separators_not_removed():
    # 20 chars is NOT "longer than 20" — kept. (Three identical messages
    # still collapse, and the separator must survive inside the kept one.)
    sep = "=" * 20
    messages = [_msg("tool", f"{sep}\nX")] * 3
    out = shake(messages)
    assert len(out) == 1
    assert out[0]["content"] == f"{sep}\nX\n(repeated 3x)"


def test_non_decorative_lines_not_removed():
    # A "line" that is mostly = but contains letters is not a banner.
    line = "=" * 25 + " SECTION " + "=" * 25
    messages = [_msg("tool", f"{line}\nA")] * 4
    out = shake(messages)
    assert len(out) == 1
    assert line in out[0]["content"]


def test_banners_cleaned_in_collapsed_run():
    banner = "*" * 30
    messages = [
        _msg("tool", f"{banner}\nstatus ok"),
        _msg("tool", f"{banner}\nstatus ok"),
        _msg("tool", f"{banner}\nstatus ok"),
    ]
    out = shake(messages)
    assert len(out) == 1
    assert banner not in out[0]["content"]
    assert out[0]["content"] == "status ok\n(repeated 3x)"


# ---------------------------------------------------------------------------
# Never drop the last occurrence of anything
# ---------------------------------------------------------------------------


def test_last_occurrence_of_run_kept():
    messages = [
        _msg("user", "again"),
        _msg("tool", "result", tool_call_id="call_1"),
        _msg("tool", "result", tool_call_id="call_2"),
        _msg("tool", "result", tool_call_id="call_3"),
    ]
    out = shake(messages)
    assert out[-1]["role"] == "tool"
    assert out[-1]["content"] == "result\n(repeated 3x)"
    # Metadata of the LAST occurrence survives.
    assert out[-1]["tool_call_id"] == "call_3"


def test_final_message_never_dropped():
    messages = [
        _msg("tool", "dup"),
        _msg("tool", "dup"),
        _msg("tool", "dup"),
        _msg("tool", "dup"),
    ]
    out = shake(messages)
    assert len(out) == 1
    assert out[0]["role"] == "tool"
    assert out[0]["content"] == "dup\n(repeated 4x)"


# ---------------------------------------------------------------------------
# Purity: input never mutated, output is a new list, deterministic
# ---------------------------------------------------------------------------


def test_input_not_mutated():
    messages = [
        _msg("user", "hello"),
        _msg("tool", "x"),
        _msg("tool", "x"),
        _msg("assistant", "ok"),
    ]
    snapshot = copy.deepcopy(messages)
    shake(messages)
    assert messages == snapshot


def test_returns_new_list():
    messages = [_msg("tool", "a")]
    out = shake(messages)
    assert out is not messages


def test_empty_input():
    assert shake([]) == []


def test_deterministic():
    messages = [
        _msg("user", "go"),
        _msg("tool", "boom"),
        _msg("tool", "boom"),
        _msg("tool", "boom"),
        _msg("assistant", "ok"),
    ]
    assert shake(messages) == shake(messages)
