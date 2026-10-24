#!/usr/bin/env python3

# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""TDD tests for visible-range snapshot provenance (R1 Task 07).

A read may only authorize the lines it actually DISPLAYED, and only for the
task that displayed them.  These tests drive the real public paths — the
``read_file`` / ``search_files`` handlers feed the ``edit`` hashline handler
through the task-scoped snapshot registry — never the store internals alone.
"""

import json
import re

import pytest

import tools.file_tools as file_tools
from tools.edit_tool import _handle_edit
from tools.file_operations import SearchMatch, SearchResult, ShellFileOperations
from tools.file_tools import _handle_search_files, read_file_tool
from tools.hashline.snapshots import compute_tag, task_stores

_HEADER_RE = re.compile(r"^\[(.+?)#([0-9A-F]{4})\]$")

#: Common substring of the seen-lines-only refusals (line and range variants).
NOT_SEEN = "you have seen"

#: Exact contract message for an edit with no observed snapshot.
READ_FIRST = (
    "Read the target lines before the edit. The current task has no "
    "observed snapshot for this file."
)


def _tag_of(header: str) -> str:
    match = _HEADER_RE.match(header)
    assert match is not None, header
    return match.group(2)


# ---------------------------------------------------------------------------
# Fakes: a file backend that numbers/truncates lines exactly like the real one
# ---------------------------------------------------------------------------


class _FakeReadResult:
    def __init__(self, content="", total_lines=0, file_size=0, truncated=False):
        self.content = content
        self._total_lines = total_lines
        self._file_size = file_size
        self._truncated = truncated

    def to_dict(self):
        d = {
            "content": self.content,
            "total_lines": self._total_lines,
            "file_size": self._file_size,
        }
        if self._truncated:
            d["truncated"] = True
        return d


class _FakeFileOps:
    """Serves a numbered window + raw full text for one in-memory file."""

    def __init__(self, full_text, search_result=None):
        self.full_text = full_text
        lines = full_text.split("\n")
        if full_text.endswith("\n"):
            lines = lines[:-1]
        self.lines = lines
        self.search_result = search_result

    def read_file(self, path, offset=1, limit=500):
        window = self.lines[offset - 1 : offset - 1 + limit]
        # The REAL numbering/truncation helper, so long-line truncation is
        # exercised rather than simulated.
        numbered = ShellFileOperations._add_line_numbers(  # type: ignore[arg-type]
            None, "\n".join(window), offset
        )
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

    def search(self, **kwargs):
        return self.search_result


def _install_ops(monkeypatch, ops):
    monkeypatch.setattr(file_tools, "_get_file_ops", lambda tid="default": ops)


def _write(tmp_path, name, lines):
    f = tmp_path / name
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return f


def _read(f, task_id, **kwargs):
    """Read through the real read handler; return (parsed_result, header)."""
    result = json.loads(read_file_tool(str(f), task_id=task_id, **kwargs))
    body = result.get("content", "")
    first = body.split("\n", 1)[0]
    match = _HEADER_RE.match(first)
    assert match is not None, body
    return result, first


def _edit(f, tag, body, task_id):
    payload = f"[{f}#{tag}]\n{body}"
    return json.loads(_handle_edit({"input": payload, "mode": "hashline"}, task_id=task_id))


@pytest.fixture(autouse=True)
def _clean_task_stores():
    yield
    for tid in ("task-a", "task-b", "task-s", "task-t", "task-u"):
        task_stores.discard(tid)


# ---------------------------------------------------------------------------
# Reads record the displayed lines
# ---------------------------------------------------------------------------


def test_read_emits_header_and_records_the_full_window(tmp_path, monkeypatch):
    f = _write(tmp_path, "greet.py", [f"line {i}" for i in range(1, 6)])
    content = f.read_text(encoding="utf-8")
    _install_ops(monkeypatch, _FakeFileOps(content))

    result, header = _read(f, "task-a")

    assert header == f"[{f}#{compute_tag(content)}]"
    snap = task_stores.for_task("task-a").get(str(f))
    assert snap is not None
    assert snap.tag == compute_tag(content)
    assert snap.visible_ranges == ((1, 5),)
    assert "1|line 1" in result["content"]


def test_partial_read_records_only_the_displayed_window(tmp_path, monkeypatch):
    f = _write(tmp_path, "big.py", [f"line {i}" for i in range(1, 11)])
    _install_ops(monkeypatch, _FakeFileOps(f.read_text(encoding="utf-8")))

    _read(f, "task-a", offset=1, limit=3)

    snap = task_stores.for_task("task-a").get(str(f))
    assert snap is not None
    assert snap.visible_ranges == ((1, 3),)


def test_two_tasks_do_not_share_observed_reads(tmp_path, monkeypatch):
    f = _write(tmp_path, "shared.py", [f"line {i}" for i in range(1, 6)])
    _install_ops(monkeypatch, _FakeFileOps(f.read_text(encoding="utf-8")))

    _, header = _read(f, "task-a")
    tag = _tag_of(header)

    # task-b never read the file: task-a's header must not authorize it.
    out = _edit(f, tag, "PUT 2.=2:\n+STOLEN\n", task_id="task-b")

    assert "error" in out, out
    assert READ_FIRST in out["error"], out
    assert f.read_text(encoding="utf-8").splitlines()[1] == "line 2"
    assert task_stores.for_task("task-b").get(str(f)) is None


# ---------------------------------------------------------------------------
# Seen-lines only: an unseen line is never editable
# ---------------------------------------------------------------------------


def test_partial_read_cannot_authorize_an_unseen_line(tmp_path, monkeypatch):
    f = _write(tmp_path, "wide.py", [f"line {i}" for i in range(1, 11)])
    _install_ops(monkeypatch, _FakeFileOps(f.read_text(encoding="utf-8")))

    _, header = _read(f, "task-a", offset=1, limit=3)
    tag = _tag_of(header)

    unseen = _edit(f, tag, "PUT 8.=8:\n+SNEAK\n", task_id="task-a")
    assert "error" in unseen, unseen
    assert NOT_SEEN in unseen["error"], unseen

    seen = _edit(f, tag, "PUT 2.=2:\n+EDITED\n", task_id="task-a")
    assert seen.get("ok") is True, seen
    assert f.read_text(encoding="utf-8").splitlines()[1] == "EDITED"


def test_full_read_then_edit_on_a_displayed_line_applies(tmp_path, monkeypatch):
    f = _write(tmp_path, "full.py", [f"line {i}" for i in range(1, 6)])
    _install_ops(monkeypatch, _FakeFileOps(f.read_text(encoding="utf-8")))

    _, header = _read(f, "task-a", full=True)
    tag = _tag_of(header)

    out = _edit(f, tag, "PUT 3.=3:\n+REPLACED\n", task_id="task-a")
    assert out.get("ok") is True, out
    assert f.read_text(encoding="utf-8").splitlines()[2] == "REPLACED"


def test_truncated_line_is_not_authorized(tmp_path, monkeypatch):
    from tools.tool_output_limits import get_max_line_length

    huge = "x" * (get_max_line_length() + 50)
    f = _write(tmp_path, "long.py", ["line 1", huge, "line 3"])
    _install_ops(monkeypatch, _FakeFileOps(f.read_text(encoding="utf-8")))

    result, header = _read(f, "task-a")
    tag = _tag_of(header)
    assert "... [truncated]" in result["content"]

    # Only lines 1 and 3 were fully displayed.
    snap = task_stores.for_task("task-a").get(str(f))
    assert snap is not None
    assert snap.visible_ranges == ((1, 1), (3, 3))

    refused = _edit(f, tag, "PUT 2.=2:\n+SHORT\n", task_id="task-a")
    assert "error" in refused, refused
    assert NOT_SEEN in refused["error"], refused

    allowed = _edit(f, tag, "PUT 3.=3:\n+DONE\n", task_id="task-a")
    assert allowed.get("ok") is True, allowed


# ---------------------------------------------------------------------------
# Unknown / stale snapshots: refuse and hand back the read-first contract
# ---------------------------------------------------------------------------


def test_unknown_snapshot_returns_the_exact_read_first_error(tmp_path, monkeypatch):
    f = _write(tmp_path, "fresh.py", ["a", "b", "c"])
    _install_ops(monkeypatch, _FakeFileOps(f.read_text(encoding="utf-8")))
    tag = compute_tag(f.read_text(encoding="utf-8"))

    out = _edit(f, tag, "PUT 2.=2:\n+X\n", task_id="task-a")

    assert "error" in out, out
    assert READ_FIRST in out["error"], out
    # The edit path must not record anything: a retry without a read fails
    # exactly the same way, and the file is untouched.
    assert task_stores.for_task("task-a").get(str(f)) is None
    assert f.read_text(encoding="utf-8") == "a\nb\nc\n"
    again = _edit(f, tag, "PUT 2.=2:\n+X\n", task_id="task-a")
    assert READ_FIRST in again["error"], again


def test_unknown_snapshot_hint_names_the_header_a_read_will_emit(tmp_path, monkeypatch):
    f = _write(tmp_path, "hint.py", ["a", "b", "c"])
    _install_ops(monkeypatch, _FakeFileOps(f.read_text(encoding="utf-8")))
    tag = compute_tag(f.read_text(encoding="utf-8"))

    out = _edit(f, tag, "PUT 2.=2:\n+X\n", task_id="task-a")

    assert f"[{f}#{tag}]" in out["error"], out

    # ... and after a real re-read, the same edit applies.
    _, header = _read(f, "task-a")
    assert header == f"[{f}#{tag}]"
    applied = _edit(f, tag, "PUT 2.=2:\n+X\n", task_id="task-a")
    assert applied.get("ok") is True, applied


def test_stale_tag_after_content_change_cannot_authorize(tmp_path, monkeypatch):
    f = _write(tmp_path, "drift.py", [f"line {i}" for i in range(1, 7)])
    _install_ops(monkeypatch, _FakeFileOps(f.read_text(encoding="utf-8")))

    _, first_header = _read(f, "task-a")
    stale_tag = _tag_of(first_header)

    # The file changes on disk and the task re-reads it: the head snapshot is
    # now the new content, so the first tag is stale.
    f.write_text(
        "\n".join(
            ["line 1", "line 2", "line 3", "line 4", "CHANGED 5", "line 6"]
        )
        + "\n",
        encoding="utf-8",
    )
    _install_ops(monkeypatch, _FakeFileOps(f.read_text(encoding="utf-8")))
    _, second_header = _read(f, "task-a")
    assert _tag_of(second_header) != stale_tag

    out = _edit(f, stale_tag, "PUT 5.=5:\n+OVERWRITTEN\n", task_id="task-a")

    assert "error" in out, out
    assert "re-read" in out["error"], out
    assert f.read_text(encoding="utf-8").splitlines()[4] == "CHANGED 5"


# ---------------------------------------------------------------------------
# Reads and searches never fail because of provenance bookkeeping
# ---------------------------------------------------------------------------


def test_anonymous_read_still_returns_content_without_a_header(tmp_path, monkeypatch):
    f = _write(tmp_path, "anon.py", ["a", "b", "c"])
    _install_ops(monkeypatch, _FakeFileOps(f.read_text(encoding="utf-8")))

    result = json.loads(read_file_tool(str(f), task_id="default"))

    assert "error" not in result, result
    assert "1|a" in result["content"]
    assert not result["content"].startswith("[")


# ---------------------------------------------------------------------------
# Search records only the matched displayed lines
# ---------------------------------------------------------------------------


def _search_result(path, matches):
    return SearchResult(
        matches=[SearchMatch(path=str(path), line_number=n, content=c) for n, c in matches],
        total_count=len(matches),
    )


def test_search_records_only_matched_displayed_lines(tmp_path, monkeypatch):
    f = _write(tmp_path, "grep.py", [f"line {i}" for i in range(1, 9)])
    content = f.read_text(encoding="utf-8")
    ops = _FakeFileOps(
        content, search_result=_search_result(f, [(3, "line 3"), (7, "line 7")])
    )
    _install_ops(monkeypatch, ops)

    out = json.loads(
        _handle_search_files({"pattern": "line", "path": str(f)}, task_id="task-s")
    )
    assert out["total_count"] == 2, out

    snap = task_stores.for_task("task-s").get(str(f))
    assert snap is not None
    assert snap.visible_ranges == ((3, 3), (7, 7))

    tag = compute_tag(content)
    applied = _edit(f, tag, "PUT 3.=3:\n+GREPPED\n", task_id="task-s")
    assert applied.get("ok") is True, applied


def test_search_does_not_authorize_an_unmatched_line(tmp_path, monkeypatch):
    f = _write(tmp_path, "grep2.py", [f"line {i}" for i in range(1, 9)])
    content = f.read_text(encoding="utf-8")
    ops = _FakeFileOps(
        content, search_result=_search_result(f, [(3, "line 3"), (7, "line 7")])
    )
    _install_ops(monkeypatch, ops)

    json.loads(_handle_search_files({"pattern": "line", "path": str(f)}, task_id="task-s"))
    tag = compute_tag(content)

    out = _edit(f, tag, "PUT 5.=5:\n+NOPE\n", task_id="task-s")

    assert "error" in out, out
    assert NOT_SEEN in out["error"], out
    assert f.read_text(encoding="utf-8").splitlines()[4] == "line 5"


def test_search_records_nothing_when_match_content_is_capped(tmp_path, monkeypatch):
    """A 500-char match line may have been cut: authorize nothing for it."""
    f = _write(tmp_path, "grep3.py", ["line 1", "line 2", "line 3"])
    content = f.read_text(encoding="utf-8")
    ops = _FakeFileOps(content, search_result=_search_result(f, [(2, "y" * 500)]))
    _install_ops(monkeypatch, ops)

    json.loads(_handle_search_files({"pattern": "line", "path": str(f)}, task_id="task-s"))

    assert task_stores.for_task("task-s").get(str(f)) is None
    out = _edit(f, compute_tag(content), "PUT 2.=2:\n+NOPE\n", task_id="task-s")
    assert "error" in out, out
    assert READ_FIRST in out["error"], out
    assert f.read_text(encoding="utf-8").splitlines()[1] == "line 2"

def test_successful_edit_does_not_widen_observation(tmp_path, monkeypatch):
    """A successful edit must not authorize lines the task never saw."""
    f = _write(tmp_path, "narrow.py", [f"line {i}" for i in range(1, 11)])
    _install_ops(monkeypatch, _FakeFileOps(f.read_text(encoding="utf-8")))

    _, header = _read(f, "task-a", offset=1, limit=3)
    tag = _tag_of(header)

    first = _edit(f, tag, "PUT 2.=2:\n+FIRST\n", task_id="task-a")
    assert first.get("ok") is True, first
    snap = task_stores.for_task("task-a").get(str(f))
    assert snap is not None
    assert snap.visible_ranges == ()

    # Line 8 was never displayed; the fresh tag after the edit must not
    # authorize it, so a successful edit cannot widen the observed window.
    unseen = _edit(f, snap.tag, "PUT 8.=8:\n+SNEAK\n", task_id="task-a")
    assert "error" in unseen, unseen
    assert NOT_SEEN in unseen["error"], unseen
    assert f.read_text(encoding="utf-8").splitlines()[7] == "line 8"
