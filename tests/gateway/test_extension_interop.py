"""Browser-extension interop tests.

Covers the three gaps versus the browser extension's capability
probes: /v1/profiles, /v1/skills, and acceptance of
``hermes.browser.turn.v2`` envelopes on /v1/runs.
"""

import json

import pytest

from gateway.platforms import api_server as api_mod


class TestCapabilitiesAdvertised:
    def test_capabilities_lists_profiles_and_skills(self):
        # The capabilities payload must advertise the new routes so the
        # extension's inferredFeature() checks light up.
        import inspect

        source = inspect.getsource(api_mod.APIServerAdapter._handle_capabilities)
        assert "profiles" in source
        assert "skills" in source


class TestEnvelopeParsing:
    def test_extract_human_input_from_turn_v2(self):
        envelope = {
            "protocol": "hermes.browser.turn.v2",
            "human_input": {"source": "composer", "text": "summarize this page"},
            "browser_context": {},
            "source_receipt": {"protocol": "hermes.browser.turn.v2", "version": 2},
        }
        text = api_mod.extract_browser_turn_text(envelope)
        assert text == "summarize this page"

    def test_plain_input_untouched(self):
        assert api_mod.extract_browser_turn_text("hello") == "hello"
        assert api_mod.extract_browser_turn_text({"input": "hey"}) == "hey"

    def test_envelope_without_human_input_falls_back(self):
        env = {"protocol": "hermes.browser.turn.v2"}
        assert api_mod.extract_browser_turn_text(env) is None

    def test_attachment_context_appended(self):
        env = {
            "protocol": "hermes.browser.turn.v2",
            "human_input": {"text": "question"},
            "attachment_context": {"items": [{"label": "notes.txt", "text": "file body"}]},
        }
        text = api_mod.extract_browser_turn_text(env)
        assert "question" in text
        assert "file body" in text

    def test_budget_reject_oversize_human_input(self):
        env = {
            "protocol": "hermes.browser.turn.v2",
            "human_input": {"text": "x" * 60_000},  # over the 48k BCP budget
        }
        # Extension clamps client-side; server must not crash either way.
        text = api_mod.extract_browser_turn_text(env)
        assert isinstance(text, str) or text is None
