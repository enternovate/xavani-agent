# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.

from types import SimpleNamespace

import pytest

from xavani_cli import advisor


class TestParseNotes:
    def test_parses_all_severities(self):
        text = "[high] wrong file path\n[medium] missed edge case\n[low] naming"
        notes = advisor.parse_notes(text)
        assert [n["severity"] for n in notes] == ["high", "medium", "low"]
        assert notes[0]["note"] == "wrong file path"

    def test_caps_at_max_notes(self):
        text = "\n".join(f"[low] note {i}" for i in range(10))
        assert len(advisor.parse_notes(text)) == advisor.MAX_NOTES

    def test_ignores_preamble_and_blank_lines(self):
        text = "Here are my notes:\n\n[high] real problem\nDone."
        notes = advisor.parse_notes(text)
        assert len(notes) == 1
        assert notes[0]["note"] == "real problem"

    def test_empty_response_gives_no_notes(self):
        assert advisor.parse_notes("") == []
        assert advisor.parse_notes("(nothing to flag)") == []


class TestReviewTurn:
    def test_returns_none_when_no_advisor_model(self, monkeypatch):
        monkeypatch.setattr(advisor, "resolve_advisor_model", lambda: None)
        assert advisor.review_turn("q", "a") is None

    def test_returns_parsed_notes_from_call_llm(self, monkeypatch):
        monkeypatch.setattr(
            advisor,
            "resolve_advisor_model",
            lambda: {"provider": "p", "model": "m"},
        )
        seen = {}

        def fake_call_llm(**kwargs):
            seen.update(kwargs)
            return "[high] bug in loop"

        monkeypatch.setattr(
            "agent.auxiliary_client.call_llm", fake_call_llm
        )
        notes = advisor.review_turn("q", "a")
        assert notes == [{"severity": "high", "note": "bug in loop"}]
        assert seen["model"] == "m"
        assert seen["provider"] == "p"
        assert "<user_request>" in seen["messages"][1]["content"]

    def test_swallows_transport_errors_as_none(self, monkeypatch):
        monkeypatch.setattr(
            advisor,
            "resolve_advisor_model",
            lambda: {"provider": "p", "model": "m"},
        )

        def boom(**kwargs):
            raise RuntimeError("provider down")

        monkeypatch.setattr("agent.auxiliary_client.call_llm", boom)
        assert advisor.review_turn("q", "a") is None

    def test_reads_openai_shape_response(self, monkeypatch):
        monkeypatch.setattr(
            advisor,
            "resolve_advisor_model",
            lambda: {"provider": "p", "model": "m"},
        )
        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="[low] style"))]
        )
        monkeypatch.setattr(
            "agent.auxiliary_client.call_llm", lambda **kwargs: response
        )
        assert advisor.review_turn("q", "a") == [
            {"severity": "low", "note": "style"}
        ]


class TestMaybeReview:
    def test_passthrough_when_disabled(self):
        agent = SimpleNamespace(advisor_enabled=False)
        assert advisor.maybe_review(agent, "q", "reply") == "reply"

    def test_passthrough_when_no_notes(self, monkeypatch):
        agent = SimpleNamespace(advisor_enabled=True)
        monkeypatch.setattr(advisor, "review_turn", lambda q, a: [])
        assert advisor.maybe_review(agent, "q", "reply") == "reply"

    def test_appends_formatted_block(self, monkeypatch):
        agent = SimpleNamespace(advisor_enabled=True)
        notes = [{"severity": "high", "note": "fix the loop"}]
        monkeypatch.setattr(advisor, "review_turn", lambda q, a: notes)
        out = advisor.maybe_review(agent, "q", "reply text")
        assert out.startswith("reply text")
        assert "---" in out
        assert "[advisor notes]" in out
        assert "[high] fix the loop" in out

    def test_passthrough_on_reviewer_crash(self, monkeypatch):
        agent = SimpleNamespace(advisor_enabled=True)

        def boom(q, a):
            raise RuntimeError("unexpected")

        monkeypatch.setattr(advisor, "review_turn", boom)
        assert advisor.maybe_review(agent, "q", "reply") == "reply"
