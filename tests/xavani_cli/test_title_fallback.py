# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the /title session-naming fallback (C16)."""

from __future__ import annotations

import pytest

import cli
from xavani_state import SessionDB


class TestDeriveSessionTitleFromMessage:
    def test_single_line_normalization(self):
        assert (
            cli.derive_session_title_from_message("Fix the  tirith\n\n hang")
            == "Fix the tirith hang"
        )

    def test_strips_leading_trailing_whitespace(self):
        assert cli.derive_session_title_from_message("   hello world   ") == "hello world"

    def test_truncates_to_60_chars(self):
        long_msg = "x" * 200
        derived = cli.derive_session_title_from_message(long_msg)
        assert len(derived) == 60
        assert derived == "x" * 60

    def test_truncation_does_not_exceed_limit(self):
        derived = cli.derive_session_title_from_message("word " * 40)
        assert len(derived) <= 60

    def test_empty_inputs_return_empty(self):
        assert cli.derive_session_title_from_message(None) == ""
        assert cli.derive_session_title_from_message("") == ""
        assert cli.derive_session_title_from_message("   \n\t ") == ""
        assert cli.derive_session_title_from_message([]) == ""

    def test_multimodal_list_content(self):
        content = [
            {"type": "text", "text": "Analyze this chart"},
            {"type": "image_url", "image_url": {"url": "data:..."}},
        ]
        assert cli.derive_session_title_from_message(content) == "Analyze this chart"

    def test_derived_title_passes_sanitize_title(self):
        derived = cli.derive_session_title_from_message(
            "Some very long first user message that would make a great session title "
            "but it keeps going and going beyond any reasonable length"
        )
        assert derived
        cleaned = SessionDB.sanitize_title(derived)
        assert cleaned is not None
        assert cleaned == derived
        assert len(cleaned) <= SessionDB.MAX_TITLE_LENGTH


class TestDeriveTitleFallback:
    def _make_cli(self, history=None, session_db=None, session_id="s1"):
        instance = cli.XavaniCLI.__new__(cli.XavaniCLI)
        instance.conversation_history = history or []
        instance._session_db = session_db
        instance.session_id = session_id
        instance._pending_title = None
        return instance

    def test_derives_from_first_user_message_in_history(self):
        cli_instance = self._make_cli(
            history=[
                {"role": "system", "content": "be nice"},
                {"role": "user", "content": "Debug the login flow"},
                {"role": "assistant", "content": "ok"},
            ]
        )
        assert cli_instance._derive_title_fallback() == "Debug the login flow"

    def test_skips_leading_system_messages(self):
        cli_instance = self._make_cli(
            history=[
                {"role": "system", "content": "sys"},
                {"role": "user", "content": "first user msg"},
            ]
        )
        assert cli_instance._derive_title_fallback() == "first user msg"

    def test_empty_history_returns_none(self):
        cli_instance = self._make_cli(history=[])
        assert cli_instance._derive_title_fallback() is None

    def test_no_user_message_returns_none(self):
        cli_instance = self._make_cli(
            history=[{"role": "assistant", "content": "hi"}]
        )
        assert cli_instance._derive_title_fallback() is None

    def test_falls_back_to_session_db(self):
        class FakeDb:
            def __init__(self):
                self.rows = [
                    {"role": "assistant", "content": "hello"},
                    {"role": "user", "content": "DB user message"},
                ]

            def get_messages(self, session_id):
                return self.rows

            def get_session(self, session_id):
                # Session row doesn't exist yet → title gets queued as pending
                return None

        cli_instance = self._make_cli(history=[], session_db=FakeDb())
        assert cli_instance._derive_title_fallback() == "DB user message"
        assert cli_instance._pending_title == "DB user message"
