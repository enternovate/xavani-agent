# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.

import pytest

from xavani_cli.staged_changes import StagedChangeSet, get_change_set


@pytest.fixture
def change_set():
    return StagedChangeSet()


class TestStageAndReview:
    def test_stage_assigns_sequence(self, change_set):
        assert change_set.stage("a.py", "one") == 1
        assert change_set.stage("b.py", "two", reason="fix") == 2
        rows = change_set.pending()
        assert [r["path"] for r in rows] == ["a.py", "b.py"]
        assert rows[1]["reason"] == "fix"

    def test_render_summary_empty(self, change_set):
        assert change_set.render_diff_summary() == "No staged changes."

    def test_render_summary_lists_files(self, change_set):
        change_set.stage("a.py", "content", reason="feat")
        text = change_set.render_diff_summary()
        assert "a.py (feat)" in text
        assert "1 file(s)" in text


class TestApply:
    def test_apply_writes_all_and_clears(self, change_set, tmp_path):
        change_set.stage("sub/x.md", "# hi")
        change_set.stage("y.md", "yes")
        applied = change_set.apply(base_dir=tmp_path)
        assert len(applied) == 2
        assert (tmp_path / "sub" / "x.md").read_text(encoding="utf-8") == "# hi"
        assert change_set.pending() == []

    def test_apply_writes_absolute_paths_directly(self, change_set, tmp_path):
        target = tmp_path / "abs.md"
        change_set.stage(str(target), "abs")
        change_set.apply()
        assert target.read_text(encoding="utf-8") == "abs"


class TestReject:
    def test_reject_one_by_seq(self, change_set):
        change_set.stage("a.py", "a")
        seq = change_set.stage("b.py", "b")
        assert change_set.reject(seq) == 1
        assert [r["path"] for r in change_set.pending()] == ["a.py"]

    def test_reject_all(self, change_set):
        change_set.stage("a.py", "a")
        change_set.stage("b.py", "b")
        assert change_set.reject() == 2
        assert change_set.pending() == []


class TestRegistry:
    def test_session_keys_isolate_sets(self):
        one = get_change_set(session_key=101)
        two = get_change_set(session_key=202)
        assert one is not two
        assert get_change_set(session_key=101) is one
