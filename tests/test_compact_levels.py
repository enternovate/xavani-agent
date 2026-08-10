# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

from contextlib import nullcontext

from cli import XavaniCLI


class DummyAgent:
    def __init__(self):
        self.compression_enabled = True
        self._cached_system_prompt = "FULL CACHED SYSTEM PROMPT SHOULD NOT BE NESTED"
        self.session_id = "new-session"
        self.calls = []

    def _compress_context(self, messages, system_message, *, approx_tokens=None, focus_topic=None, force=False):
        self.calls.append(
            {
                "messages": messages,
                "system_message": system_message,
                "approx_tokens": approx_tokens,
                "focus_topic": focus_topic,
                "force": force,
            }
        )
        return ([{"role": "user", "content": "[CONTEXT SUMMARY]: compacted"}], "new system prompt")


class ExplodingAgent(DummyAgent):
    def _compress_context(self, *args, **kwargs):
        raise AssertionError("LLM compaction must not run at level 1")


def _make_cli(agent=None, history=None):
    cli = XavaniCLI.__new__(XavaniCLI)
    cli.conversation_history = history if history is not None else [
        {"role": "user", "content": "one"},
        {"role": "assistant", "content": "two"},
        {"role": "user", "content": "three"},
        {"role": "assistant", "content": "four"},
    ]
    cli.agent = agent if agent is not None else DummyAgent()
    cli.session_id = "old-session"
    cli._pending_title = "old title"
    cli._busy_command = lambda _message: nullcontext()
    return cli


def _patch_feedback(monkeypatch):
    monkeypatch.setattr(
        "agent.manual_compression_feedback.summarize_manual_compression",
        lambda *args, **kwargs: {
            "noop": False,
            "headline": "compressed",
            "token_line": "tokens reduced",
            "note": "",
        },
    )


def test_no_argument_keeps_default_behavior(monkeypatch, capsys):
    _patch_feedback(monkeypatch)
    cli = _make_cli()
    cli._manual_compress("/compress")
    assert len(cli.agent.calls) == 1
    call = cli.agent.calls[0]
    assert call["system_message"] is None
    assert call["focus_topic"] is None
    assert call["force"] is True
    assert cli.session_id == "new-session"
    out = capsys.readouterr().out
    assert "Compressing" in out
    assert "Shake" not in out


def test_level1_shakes_and_never_calls_llm(capsys):
    history = [
        {"role": "user", "content": "one"},
        {"role": "assistant", "content": "two"},
        {"role": "tool", "content": "ls\nfoo\nbar"},
        {"role": "tool", "content": "ls\nfoo\nbar"},
        {"role": "user", "content": "three"},
    ]
    cli = _make_cli(agent=ExplodingAgent(), history=history)
    cli._manual_compress("/compress 1")
    assert cli.agent.calls == []
    joined = " ".join(m["content"] for m in cli.conversation_history)
    assert "(repeated 2x)" in joined
    assert len(cli.conversation_history) == 4
    out = capsys.readouterr().out
    assert "Shake only" in out


def test_level1_works_when_compression_disabled():
    history = [
        {"role": "user", "content": "one"},
        {"role": "assistant", "content": "two"},
        {"role": "tool", "content": "same"},
        {"role": "tool", "content": "same"},
        {"role": "user", "content": "three"},
    ]
    agent = DummyAgent()
    agent.compression_enabled = False
    cli = _make_cli(agent=agent, history=history)
    cli._manual_compress("/compact 1")
    assert "(repeated 2x)" in " ".join(m["content"] for m in cli.conversation_history)


def test_level2_shakes_before_summarizing(monkeypatch):
    _patch_feedback(monkeypatch)
    history = [
        {"role": "user", "content": "one"},
        {"role": "assistant", "content": "two"},
        {"role": "tool", "content": "dupe output"},
        {"role": "tool", "content": "dupe output"},
        {"role": "user", "content": "three"},
    ]
    cli = _make_cli(history=history)
    cli._manual_compress("/compress 2")
    assert len(cli.agent.calls) == 1
    sent = cli.agent.calls[0]["messages"]
    assert "(repeated 2x)" in " ".join(m["content"] for m in sent)


def test_level3_routes_to_full_compaction(monkeypatch):
    _patch_feedback(monkeypatch)
    cli = _make_cli()
    cli._manual_compress("/compress 3")
    assert len(cli.agent.calls) == 1
    call = cli.agent.calls[0]
    assert call["force"] is True
    assert call["focus_topic"] is None


def test_level3_with_focus_topic(monkeypatch):
    _patch_feedback(monkeypatch)
    cli = _make_cli()
    cli._manual_compress("/compact 3 database schema")
    assert len(cli.agent.calls) == 1
    assert cli.agent.calls[0]["focus_topic"] == "database schema"


def test_invalid_level_errors_without_state_change(capsys):
    history = [
        {"role": "user", "content": "one"},
        {"role": "assistant", "content": "two"},
        {"role": "user", "content": "three"},
        {"role": "assistant", "content": "four"},
    ]
    for bad in ("0", "4", "-1"):
        cli = _make_cli(history=[dict(m) for m in history])
        cli._manual_compress(f"/compress {bad}")
        assert cli.agent.calls == []
        assert cli.conversation_history == history
        assert cli.session_id == "old-session"
        out = capsys.readouterr().out
        assert "Invalid" in out and "1" in out and "2" in out and "3" in out


def test_compact_alias_dispatches_to_same_handler(capsys):
    history = [
        {"role": "user", "content": "one"},
        {"role": "assistant", "content": "two"},
        {"role": "tool", "content": "dup"},
        {"role": "tool", "content": "dup"},
        {"role": "user", "content": "three"},
    ]
    cli = _make_cli(agent=ExplodingAgent(), history=history)
    cli.config = {}
    cli.process_command("/compact 1")
    assert cli.agent.calls == []
    assert "(repeated 2x)" in " ".join(m["content"] for m in cli.conversation_history)


def test_legacy_focus_topic_still_works(monkeypatch):
    _patch_feedback(monkeypatch)
    cli = _make_cli()
    cli._manual_compress("/compress database schema")
    assert len(cli.agent.calls) == 1
    assert cli.agent.calls[0]["focus_topic"] == "database schema"
