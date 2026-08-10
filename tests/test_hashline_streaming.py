"""Tests for the hashline streaming edit preview (Task 18).

Covers ``preview_parse`` (best-effort parse of a PARTIAL hashline payload
that never raises) and ``diff_sections`` (read-only per-section preview
against the snapshot store that never mutates it).
"""

import pytest

from tools.hashline import parse
from tools.hashline.snapshots import SnapshotStore
from tools.hashline.streaming import diff_sections, preview_parse


def make_store(path, content, ranges=None):
    store = SnapshotStore()
    if ranges is None:
        ranges = [(1, content.count("\n") or 1)]
    store.record(path, content, ranges=ranges)
    return store


# ---------------------------------------------------------------------------
# preview_parse
# ---------------------------------------------------------------------------


def test_preview_parse_complete_payload():
    text = (
        "[greet.py#A1B2]\n"
        "PUT 1.=1:\n"
        "+def greet(name):\n"
        '+    print(f"Hi, {name}")\n'
        "[util.py#C3D4]\n"
        "PUT >$:\n"
        "+import greet\n"
    )
    result = preview_parse(text)
    assert result["complete"] is True
    assert result["error"] is None
    assert [sec.path for sec in result["sections"]] == ["greet.py", "util.py"]
    assert len(result["sections"][0].ops) == 1


def test_preview_parse_truncated_mid_body_trims_tail():
    # Last op is truncated mid-typing: "PUT 2.=2" lacks the ':' header (or a
    # register), so the strict parser rejects it. Trimming the in-flight tail
    # line must recover the completed leading section.
    text = (
        "[greet.py#A1B2]\n"
        "PUT 1.=1:\n"
        "+def greet(name):\n"
        "PUT 2.=2"
    )
    result = preview_parse(text)  # must not raise
    assert result["complete"] is True
    assert result["error"] is None
    assert [sec.path for sec in result["sections"]] == ["greet.py"]
    assert len(result["sections"]) == 1


def test_preview_parse_truncated_mid_header_incomplete():
    # Header line cut off before the closing ']' — trimming the tail can
    # never recover a section, so the result is incomplete with an error.
    text = "[greet.py#A1B"
    result = preview_parse(text)  # must not raise
    assert result["complete"] is False
    assert result["sections"] == []
    assert result["error"]


def test_preview_parse_truncated_op_line_falls_back_incomplete():
    # A payload that never reaches a parseable shape reports incomplete.
    result = preview_parse("[greet.py#A1B2]\nPUT 1")
    assert result["complete"] is False
    assert result["sections"] == []
    assert result["error"]


def test_preview_parse_empty_text_never_raises():
    for text in ("", "   \n", "*** Begin Patch\n"):
        result = preview_parse(text)
        assert result["complete"] is False
        assert result["sections"] == []
        assert result["error"]


def test_preview_parse_non_string_never_raises():
    result = preview_parse(123)  # type: ignore[arg-type]
    assert result["complete"] is False
    assert result["sections"] == []
    assert result["error"]


# ---------------------------------------------------------------------------
# diff_sections
# ---------------------------------------------------------------------------


def test_diff_sections_returns_changed_line_info():
    store = make_store("greet.py", "old1\nold2\nold3\n", ranges=[(1, 3)])
    sec = parse("[greet.py#%s]\nPUT 2.=2:\n+NEW2\n" % store.get("greet.py").tag)[0]
    previews = diff_sections(store, [sec])
    assert len(previews) == 1
    entry = previews[0]
    assert entry["path"] == "greet.py"
    assert entry["action"] == "edit"
    assert entry["base_lines"] == 3
    assert entry["result_lines"] == 3
    assert entry["error"] is None
    assert any(ln.startswith("-") for ln in entry["changed_lines"])
    assert any(ln.startswith("+") for ln in entry["changed_lines"])
    assert any("NEW2" in ln for ln in entry["changed_lines"])


def test_diff_sections_handles_multi_section_and_remove():
    store = make_store("a.py", "x\ny\nz\n", ranges=[(1, 3)])
    store.record("gone.py", "p\nq\n", ranges=[(1, 2)])
    tag_a = store.get("a.py").tag
    tag_gone = store.get("gone.py").tag
    sections = parse(
        f"[a.py#{tag_a}]\nPUT >1:\n+INS\n"
        f"[gone.py#{tag_gone}]\nREM\n"
    )
    previews = diff_sections(store, sections)
    by_path = {p["path"]: p for p in previews}
    assert by_path["a.py"]["action"] == "edit"
    assert by_path["a.py"]["result_lines"] == 4
    assert by_path["gone.py"]["action"] == "remove"
    assert by_path["gone.py"]["result_lines"] == 0


def test_diff_sections_does_not_modify_store():
    store = make_store("greet.py", "one\ntwo\nthree\n", ranges=[(1, 3)])
    tag_before = store.get("greet.py").tag
    content_before = store.get("greet.py").content
    path_count_before = len(store)

    sec = parse("[greet.py#%s]\nPUT 2.=3:\n+TWO\n+THREE\n" % tag_before)[0]
    diff_sections(store, [sec])

    assert len(store) == path_count_before
    assert store.get("greet.py").content == content_before
    assert store.get("greet.py").tag == tag_before


def test_diff_sections_missing_snapshot_reports_error():
    store = make_store("a.py", "x\n", ranges=[(1, 1)])
    sec = parse("[missing.py#ABCD]\nPUT 1.=1:\n+Y\n")[0]
    previews = diff_sections(store, [sec])
    assert previews[0]["path"] == "missing.py"
    assert previews[0]["action"] == "error"
    assert previews[0]["error"]
    # The valid section is still previewed — errors are per-section.
    assert len(previews) == 1
