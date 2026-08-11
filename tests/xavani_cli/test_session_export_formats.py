# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for session export HTML/MD renderers + file output."""

from __future__ import annotations

import html as html_mod
from datetime import datetime, timezone

import pytest

from xavani_cli.session_export_html import sessions_to_html
from xavani_cli.session_export_md import sessions_to_markdown

pytestmark = pytest.mark.integration

# The suite pins TZ=UTC (tests/conftest.py) for deterministic runtime, so
# expectations must be computed in UTC — naive fromtimestamp() at module
# import would use the ambient (non-UTC) timezone and mismatch the renderer.
EXPECTED_TS = datetime.fromtimestamp(1783267200.0, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

SAMPLE_SESSION = {
    "id": "20260804_100000_abcd12",
    "title": "Fix tirith hang",
    "source": "cli",
    "created_at": "2026-08-04T10:00:00",
    "last_active": "2026-08-04T10:30:00",
    "messages": [
        {
            "role": "user",
            "content": "Debug the tirith <hang> & check /tmp",
            "timestamp": 1783267200.0,
        },
        {
            "role": "assistant",
            "content": "Let me inspect.",
            "timestamp": 1783267205.0,
            "finish_reason": "tool_calls",
            "tool_calls": [
                {
                    "function": {
                        "name": "read_file",
                        "arguments": '{"path": "/tmp/x"}',
                    }
                }
            ],
        },
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "Here is the image:"},
                {"type": "image_url", "image_url": {"url": "data:..."}},
            ],
            "timestamp": 1783267210.0,
        },
        {
            "role": "tool",
            "tool_name": "read_file",
            "content": "file contents",
            "timestamp": 1783267212.0,
        },
    ],
}


class TestHtmlExport:
    def test_renders_standalone_document(self):
        doc = sessions_to_html([SAMPLE_SESSION])
        assert doc.startswith("<!DOCTYPE html>")
        assert "<title>Xavani session export</title>" in doc
        assert "Fix tirith hang" in doc
        assert "20260804_100000_abcd12" in doc

    def test_escapes_user_content(self):
        doc = sessions_to_html([SAMPLE_SESSION])
        raw = "Debug the tirith <hang> & check /tmp"
        assert raw not in doc  # never raw
        assert html_mod.escape(raw) in doc

    def test_includes_roles_and_timestamps(self):
        doc = sessions_to_html([SAMPLE_SESSION])
        assert 'class="msg user"' in doc
        assert 'class="msg tool"' in doc
        assert EXPECTED_TS in doc

    def test_summarizes_tool_calls(self):
        doc = sessions_to_html([SAMPLE_SESSION])
        assert "read_file(" in doc
        assert "🔧" in doc
        # arguments are HTML-escaped inside the summary
        assert html_mod.escape('{"path": "/tmp/x"}') in doc

    def test_multimodal_content_flattened(self):
        doc = sessions_to_html([SAMPLE_SESSION])
        assert "Here is the image:" in doc
        assert "[image]" in doc

    def test_empty_session_list(self):
        doc = sessions_to_html([])
        assert "<body>" in doc

    def test_writes_to_tmp_path(self, tmp_path):
        out = tmp_path / "export.html"
        out.write_text(sessions_to_html([SAMPLE_SESSION]), encoding="utf-8")
        assert out.is_file()
        content = out.read_text(encoding="utf-8")
        assert "Fix tirith hang" in content
        assert "read_file" in content


class TestMarkdownExport:
    def test_renders_document(self):
        doc = sessions_to_markdown([SAMPLE_SESSION])
        assert doc.startswith("# Fix tirith hang")
        assert "**Session**: `20260804_100000_abcd12`" in doc
        assert "**Source**: cli" in doc
        assert "**Messages**: 4" in doc

    def test_includes_role_headings_and_timestamps(self):
        doc = sessions_to_markdown([SAMPLE_SESSION])
        assert f"### user — {EXPECTED_TS}" in doc
        assert "### assistant" in doc
        assert "### tool" in doc

    def test_summarizes_tool_calls(self):
        doc = sessions_to_markdown([SAMPLE_SESSION])
        assert "`read_file(" in doc
        assert '{"path": "/tmp/x"}' in doc

    def test_content_preserved(self):
        doc = sessions_to_markdown([SAMPLE_SESSION])
        assert "Debug the tirith <hang> & check /tmp" in doc
        assert "Here is the image:" in doc
        assert "[image]" in doc

    def test_writes_to_tmp_path(self, tmp_path):
        out = tmp_path / "export.md"
        out.write_text(sessions_to_markdown([SAMPLE_SESSION]), encoding="utf-8")
        assert out.is_file()
        content = out.read_text(encoding="utf-8")
        assert "# Fix tirith hang" in content
        assert "### tool" in content

    def test_multiple_sessions_separated(self):
        other = {
            "id": "s2",
            "title": "Second",
            "messages": [{"role": "user", "content": "hi", "timestamp": 1.0}],
        }
        doc = sessions_to_markdown([SAMPLE_SESSION, other])
        assert doc.count("\n---\n") == 1
        assert "# Second" in doc
