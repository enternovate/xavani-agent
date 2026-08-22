# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for tools/write_journal.py — capture, commit, rollback semantics."""

import json

import pytest

from tools import write_journal


@pytest.fixture
def jdir(tmp_path, monkeypatch):
    monkeypatch.setenv("XAVANI_WRITE_JOURNAL_DIR", str(tmp_path / "journal"))
    return tmp_path / "journal"


def test_rollback_restores_prior_content(jdir, tmp_path):
    target = tmp_path / "file.txt"
    target.write_text("original", encoding="utf-8")
    entry = write_journal.capture(str(target))
    target.write_text("mutated", encoding="utf-8")
    assert write_journal.commit(entry, directory=jdir) is True

    restored = write_journal.rollback_last(1, directory=jdir)

    assert restored == [f"restored {target}"]
    assert target.read_text(encoding="utf-8") == "original"


def test_rollback_deletes_file_that_did_not_exist(jdir, tmp_path):
    target = tmp_path / "new.txt"
    entry = write_journal.capture(str(target))
    target.write_text("created", encoding="utf-8")
    write_journal.commit(entry, directory=jdir)

    restored = write_journal.rollback_last(1, directory=jdir)

    assert not target.exists()
    assert "deleted" in restored[0]


def test_commit_trims_journal_to_max_entries(jdir):
    for i in range(write_journal._MAX_ENTRIES + 5):
        entry = {"path": f"/tmp/f{i}.txt", "existed": False, "data_b64": None}
        entry["captured"] = True
        write_journal.commit(entry, directory=jdir)
    lines = (jdir / "journal.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == write_journal._MAX_ENTRIES
    assert json.loads(lines[0])["path"] == "/tmp/f5.txt"


def test_discard_prevents_commit(jdir):
    entry = write_journal.capture("/tmp/never.txt")
    write_journal.discard(entry)
    assert write_journal.commit(entry, directory=jdir) is False
    assert not (jdir / "journal.jsonl").exists()


def test_rollback_last_count_restores_in_reverse(jdir, tmp_path):
    first = tmp_path / "a.txt"
    second = tmp_path / "b.txt"
    first.write_text("A0", encoding="utf-8")
    e1 = write_journal.capture(str(first))
    first.write_text("A1", encoding="utf-8")
    write_journal.commit(e1, directory=jdir)
    second.write_text("B0", encoding="utf-8")
    e2 = write_journal.capture(str(second))
    second.write_text("B1", encoding="utf-8")
    write_journal.commit(e2, directory=jdir)

    restored = write_journal.rollback_last(2, directory=jdir)

    assert first.read_text(encoding="utf-8") == "A0"
    assert second.read_text(encoding="utf-8") == "B0"
    assert len(restored) == 2


def test_rollback_rejects_invalid_count(jdir):
    with pytest.raises(ValueError):
        write_journal.rollback_last(0, directory=jdir)


def test_commit_survives_missing_journal_dir(jdir):
    entry = {"path": "/tmp/x.txt", "existed": False, "data_b64": None, "captured": True}
    assert write_journal.commit(entry, directory=jdir) is True
