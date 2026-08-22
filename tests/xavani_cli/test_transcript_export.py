# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.

import sqlite3

import pytest

from xavani_cli import transcript_export


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "state.db"
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE messages (id INTEGER PRIMARY KEY, session_id TEXT, "
        "role TEXT, content TEXT, tool_name TEXT, timestamp TEXT)"
    )
    rows = [
        (1, "s1", "system", "you are x", None, "t0"),
        (2, "s1", "user", "hello", None, "t1"),
        (3, "s1", "assistant", "hi there", None, "t2"),
        (4, "s1", "tool", "file contents", "read_file", "t3"),
        (5, "s2", "user", "other session", None, "t4"),
        (6, "s1", "assistant", "", None, "t5"),
    ]
    conn.executemany("INSERT INTO messages VALUES (?,?,?,?,?,?)", rows)
    conn.commit()
    conn.close()
    return path


class TestCollectMessages:
    def test_filters_session_role_and_empty(self, db):
        messages = transcript_export.collect_messages(db, "s1")
        assert [m["role"] for m in messages] == ["user", "assistant", "tool"]
        assert messages[2]["tool_name"] == "read_file"


class TestRenderExport:
    def test_metadata_header_and_numbered_turns(self, db):
        messages = transcript_export.collect_messages(db, "s1")
        text = transcript_export.render_export(
            "s1", messages, model="m1", title="demo"
        )
        assert text.startswith("---\n")
        assert "session: s1" in text
        assert "model: m1" in text
        assert "messages: 3" in text
        assert "## [1] user" in text
        assert "## [3] tool (read_file)" in text

    def test_ends_with_newline(self, db):
        messages = transcript_export.collect_messages(db, "s1")
        text = transcript_export.render_export("s1", messages)
        assert text.endswith("\n")


class TestExportSession:
    def test_writes_markdown_file(self, db, tmp_path):
        out = tmp_path / "exports"
        path = transcript_export.export_session(
            db, "s1", out, model="m1", title="demo"
        )
        assert path is not None and path.is_file()
        body = path.read_text(encoding="utf-8")
        assert body.startswith("---\n")

    def test_empty_session_returns_none(self, db, tmp_path):
        assert transcript_export.export_session(db, "missing", tmp_path) is None
