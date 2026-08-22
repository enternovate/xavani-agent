# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.

import pytest

from xavani_cli import memory_tools


@pytest.fixture
def bank(tmp_path, monkeypatch):
    monkeypatch.setenv("XAVANI_MEMORY_BANK", str(tmp_path / "bank"))
    return tmp_path / "bank"


class TestRetain:
    def test_creates_entry_file(self, bank):
        record = memory_tools.retain("always run the gates", tag="rule")
        assert record["text"] == "always run the gates"
        path = bank / f"{record['id']}.md"
        assert path.is_file()
        assert "retained:" in path.read_text(encoding="utf-8")

    def test_empty_text_raises(self, bank):
        with pytest.raises(memory_tools.MemoryError):
            memory_tools.retain("   ")

    def test_source_recorded(self, bank):
        record = memory_tools.retain("fact one", source="session-9")
        body = (bank / f"{record['id']}.md").read_text(encoding="utf-8")
        assert "source: session-9" in body


class TestRecall:
    def test_all_terms_must_hit(self, bank):
        memory_tools.retain("deploy needs ruff clean")
        memory_tools.retain("deploy needs pytest green")
        memory_tools.retain("unrelated entry about cooking")
        hits = memory_tools.recall("deploy needs")
        assert len(hits) == 2
        assert len(memory_tools.recall("cooking")) == 1
        assert memory_tools.recall("zzz-nothing") == []

    def test_limit(self, bank):
        for i in range(8):
            memory_tools.retain(f"note number {i}")
        assert len(memory_tools.recall("note", limit=3)) == 3


class TestReflectAndLearn:
    def test_reflect_collects_entries(self, bank):
        memory_tools.retain("xavani targets low cost")
        memory_tools.retain("xavani targets fast median")
        reflection = memory_tools.reflect("xavani")
        assert reflection["entry_count"] == 2
        assert any("low cost" in e for e in reflection["entries"])

    def test_learn_tags_lesson(self, bank):
        record = memory_tools.learn(
            "kill exact PID not pkill -f", context="ops session"
        )
        assert record["id"].find("lesson") != -1
        assert memory_tools.promote_candidates()[0]["id"] == record["id"]

    def test_double_prefix_not_duplicated(self, bank):
        record = memory_tools.learn("lesson: already tagged")
        assert record["text"].count("lesson:") == 1


class TestMemoryEdit:
    def test_update_replaces_body(self, bank):
        record = memory_tools.retain("old text here")
        result = memory_tools.memory_edit(record["id"], new_text="new text here")
        assert result["action"] == "updated"
        body = (bank / f"{record['id']}.md").read_text(encoding="utf-8")
        assert "new text here" in body and "old text here" not in body

    def test_invalidate_marks_entry(self, bank):
        record = memory_tools.retain("soon stale", source="s1")
        result = memory_tools.memory_edit(record["id"], invalidate=True)
        assert result["action"] == "invalidated"
        body = (bank / f"{record['id']}.md").read_text(encoding="utf-8")
        assert "invalidated: yes" in body
        again = memory_tools.memory_edit(record["id"], invalidate=True)
        assert again["action"] == "invalidated"

    def test_unknown_id_raises(self, bank):
        with pytest.raises(memory_tools.MemoryError, match="no bank entry"):
            memory_tools.memory_edit("mem-missing")

    def test_update_requires_text(self, bank):
        record = memory_tools.retain("keep")
        with pytest.raises(memory_tools.MemoryError, match="new_text"):
            memory_tools.memory_edit(record["id"])


class TestMain:
    def test_retain_and_recall_roundtrip(self, bank, capsys):
        assert memory_tools.main(["retain", "gateway parity rule"]) == 0
        assert memory_tools.main(["recall", "parity"]) == 0
        out = capsys.readouterr().out
        assert "gateway parity rule" in out

    def test_error_exit_code(self, capsys):
        assert memory_tools.main(["edit", "mem-none"]) == 2
