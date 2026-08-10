#!/usr/bin/env python3

# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""TDD tests for read_file v2: [path#TAG] header + summarization + elision footer.

Verifies that:
(a) read_file_tool emits a `[path#TAG]` header whose tag matches
    compute_tag(full file content), recorded in snapshots.default_store;
(b) files over 100 lines are summarized by default: first 25 + last 25
    lines, a `...` elision marker, and a footer with concrete re-read
    ranges that actually re-read the omitted middle;
(c) files <= 100 lines return the full content plus the tag header;
(d) a summarized read records the SAME tag as the full content;
(e) explicit offset/limit windows and full=true bypass summarization.

Run with:  python3 -m pytest tests/test_read_summarization.py -q
"""

import json
import re

import pytest

import tools.file_tools as file_tools
from tools.file_tools import read_file_tool
from tools.hashline.snapshots import compute_tag, default_store

_HEADER_RE = re.compile(r"^\[(.+?)#([0-9A-F]{4})\]$")
_FOOTER_RE = re.compile(r"re-read needed ranges, e.g. (.+?):(\d+)-(\d+)\]")


class _FakeReadResult:
    """Minimal stand-in for FileOperations.read_file return value."""

    def __init__(self, content="", total_lines=0, file_size=0,
                 truncated=False, error=None):
        self.content = content
        self._total_lines = total_lines
        self._file_size = file_size
        self._truncated = truncated
        self.error = error

    def to_dict(self):
        d = {
            "content": self.content,
            "total_lines": self._total_lines,
            "file_size": self._file_size,
        }
        if self._truncated:
            d["truncated"] = True
        if self.error:
            d["error"] = self.error
        return d


class _FakeFileOps:
    """In-memory file ops serving numbered windows + raw full content."""

    def __init__(self, full_text):
        self.full_text = full_text
        self.lines = full_text.split("\n")
        if full_text.endswith("\n"):
            self.lines = self.lines[:-1]

    def read_file(self, path, offset=1, limit=500):
        window = self.lines[offset - 1: offset - 1 + limit]
        numbered = "\n".join(f"{i + offset}|{ln}" for i, ln in enumerate(window))
        return _FakeReadResult(
            content=numbered,
            total_lines=len(self.lines),
            file_size=len(self.full_text.encode("utf-8")),
            truncated=offset + limit - 1 < len(self.lines),
        )

    def read_file_raw(self, path):
        return _FakeReadResult(
            content=self.full_text,
            total_lines=len(self.lines),
            file_size=len(self.full_text.encode("utf-8")),
        )


def _make_file(tmp_path, name, n_lines, prefix="line"):
    f = tmp_path / name
    content = "".join(f"{prefix} {i}\n" for i in range(1, n_lines + 1))
    f.write_text(content, encoding="utf-8")
    return f, content


# ---------------------------------------------------------------------------
# (a) tag header
# ---------------------------------------------------------------------------


def test_tag_header_present_and_matches_compute_tag(tmp_path, monkeypatch):
    f, content = _make_file(tmp_path, "greet.py", 3)
    ops = _FakeFileOps(content)
    ops.path = str(f)
    monkeypatch.setattr(file_tools, "_get_file_ops", lambda tid="default": ops)
    default_store.invalidate(str(f))

    result = json.loads(read_file_tool(str(f), task_id="t-a"))
    body = result["content"]
    first, rest = body.split("\n", 1)
    m = _HEADER_RE.match(first)
    assert m is not None, body
    assert m.group(1) == str(f)
    assert m.group(2) == compute_tag(content)
    # line-numbered body follows the header
    assert rest.split("\n")[0] == "1|line 1"
    assert rest.split("\n")[2] == "3|line 3"


def test_tag_header_parseable_by_hashline_edit(tmp_path, monkeypatch):
    """The header is exactly the [PATH#TAG] form the hashline parser accepts."""
    from tools.hashline import parse

    f, content = _make_file(tmp_path, "greet2.py", 3)
    ops = _FakeFileOps(content)
    ops.path = str(f)
    monkeypatch.setattr(file_tools, "_get_file_ops", lambda tid="default": ops)
    default_store.invalidate(str(f))

    result = json.loads(read_file_tool(str(f), task_id="t-a2"))
    header = result["content"].split("\n", 1)[0]
    sections = parse(f"{header}\nPUT 1*:\n+X\n")
    assert sections[0].path == str(f)
    assert sections[0].tag == compute_tag(content)


# ---------------------------------------------------------------------------
# (b) summarized windowed output for large files
# ---------------------------------------------------------------------------


def test_large_file_summarized_with_elision_footer(tmp_path, monkeypatch):
    f, content = _make_file(tmp_path, "big.txt", 200)
    ops = _FakeFileOps(content)
    ops.path = str(f)
    monkeypatch.setattr(file_tools, "_get_file_ops", lambda tid="default": ops)
    default_store.invalidate(str(f))

    result = json.loads(read_file_tool(str(f), task_id="t-b"))
    body = result["content"]
    assert body.startswith(f"[{f}#"), body
    # first window
    assert "1|line 1" in body
    assert "25|line 25" in body
    # elision marker
    assert "\n...\n" in body
    # last window
    assert "176|line 176" in body
    assert "200|line 200" in body
    # footer with concrete re-read ranges
    m = _FOOTER_RE.search(body)
    assert m is not None, body
    assert m.group(1) == str(f)
    assert (int(m.group(2)), int(m.group(3))) == (26, 175)
    # summarized flag surfaced
    assert result.get("_summarized") is True

    # re-read the omitted middle via the footer range
    start, end = int(m.group(2)), int(m.group(3))
    result2 = json.loads(
        read_file_tool(str(f), offset=start, limit=end - start + 1, task_id="t-b2")
    )
    assert "50|line 50" in result2["content"]
    assert "100|line 100" in result2["content"]
    assert "175|line 175" in result2["content"]


def test_summary_elision_count_and_range(tmp_path, monkeypatch):
    f, content = _make_file(tmp_path, "big2.txt", 101)
    ops = _FakeFileOps(content)
    ops.path = str(f)
    monkeypatch.setattr(file_tools, "_get_file_ops", lambda tid="default": ops)
    default_store.invalidate(str(f))

    result = json.loads(read_file_tool(str(f), task_id="t-b3"))
    body = result["content"]
    m = _FOOTER_RE.search(body)
    assert m is not None, body
    assert (int(m.group(2)), int(m.group(3))) == (26, 76)
    assert "101|line 101" in body


# ---------------------------------------------------------------------------
# (c) small files: full content + tag, no summarization
# ---------------------------------------------------------------------------


def test_small_file_full_content_with_tag(tmp_path, monkeypatch):
    f, content = _make_file(tmp_path, "small.txt", 50)
    ops = _FakeFileOps(content)
    ops.path = str(f)
    monkeypatch.setattr(file_tools, "_get_file_ops", lambda tid="default": ops)
    default_store.invalidate(str(f))

    result = json.loads(read_file_tool(str(f), task_id="t-c"))
    body = result["content"]
    assert body.startswith(f"[{f}#{compute_tag(content)}]\n")
    assert "1|line 1" in body
    assert "50|line 50" in body
    assert "elided" not in body
    assert result.get("_summarized") is None


# ---------------------------------------------------------------------------
# (d) summary records the SAME tag as full content
# ---------------------------------------------------------------------------


def test_summary_records_same_tag_as_full_content(tmp_path, monkeypatch):
    f, content = _make_file(tmp_path, "big3.txt", 200)
    ops = _FakeFileOps(content)
    ops.path = str(f)
    monkeypatch.setattr(file_tools, "_get_file_ops", lambda tid="default": ops)
    default_store.invalidate(str(f))

    result = json.loads(read_file_tool(str(f), task_id="t-d"))
    header = result["content"].split("\n", 1)[0]
    header_tag = _HEADER_RE.match(header).group(2)

    snap = default_store.get(str(f))
    assert snap is not None
    assert snap.tag == header_tag
    assert snap.tag == compute_tag(content)
    assert snap.content == content.encode("utf-8")


# ---------------------------------------------------------------------------
# (e) explicit windows and full=true bypass summarization
# ---------------------------------------------------------------------------


def test_explicit_window_bypasses_summarization(tmp_path, monkeypatch):
    f, content = _make_file(tmp_path, "big4.txt", 200)
    ops = _FakeFileOps(content)
    ops.path = str(f)
    monkeypatch.setattr(file_tools, "_get_file_ops", lambda tid="default": ops)
    default_store.invalidate(str(f))

    result = json.loads(
        read_file_tool(str(f), offset=26, limit=150, task_id="t-e")
    )
    body = result["content"]
    assert body.startswith(f"[{f}#"), body
    assert "26|line 26" in body
    assert "100|line 100" in body
    assert "175|line 175" in body
    assert "elided" not in body
    assert result.get("_summarized") is None


def test_full_true_bypasses_summarization(tmp_path, monkeypatch):
    f, content = _make_file(tmp_path, "big5.txt", 200)
    ops = _FakeFileOps(content)
    ops.path = str(f)
    monkeypatch.setattr(file_tools, "_get_file_ops", lambda tid="default": ops)
    default_store.invalidate(str(f))

    result = json.loads(read_file_tool(str(f), full=True, task_id="t-e2"))
    body = result["content"]
    assert body.startswith(f"[{f}#"), body
    assert "1|line 1" in body
    assert "200|line 200" in body
    assert "elided" not in body
    assert result.get("_summarized") is None
