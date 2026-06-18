# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the automatic file-organizer engine (tools/file_organizer.py).

The engine moves real files on the user's machine, so the contract is
safety-first: never delete, never overwrite, skip files being written,
idempotent, and fully reversible via an undo manifest.
"""

import os
import time
from pathlib import Path

import pytest

from tools import file_organizer as fo


# ---------------------------------------------------------------------------
# categorize() — pure extension classification
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name,expected", [
    ("photo.jpg", "Images"),
    ("PHOTO.JPEG", "Images"),          # case-insensitive
    ("scan.PNG", "Images"),
    ("report.pdf", "PDFs"),
    ("notes.docx", "Documents"),
    ("essay.txt", "Documents"),
    ("budget.xlsx", "Spreadsheets"),
    ("data.csv", "Spreadsheets"),
    ("deck.pptx", "Presentations"),
    ("backup.zip", "Archives"),
    ("archive.tar.gz", "Archives"),    # double extension
    ("song.mp3", "Audio"),
    ("clip.mp4", "Video"),
    ("script.py", "Code"),
    ("config.json", "Data"),
    ("installer.dmg", "Installers"),
    ("setup.exe", "Installers"),
    ("mystery.zzz", "Other"),          # unknown extension
    ("READMENOEXT", "Other"),          # no extension
])
def test_categorize(name, expected):
    assert fo.categorize(name) == expected


def test_categorize_is_total():
    """Every input maps to a known category — never raises, never None."""
    for name in ["", ".", "a.b.c.d", "..hidden", "no.dot.here"]:
        assert fo.categorize(name) in set(fo.CATEGORY_RULES.keys()) | {"Other"}


# ---------------------------------------------------------------------------
# safe_move() — never overwrite, collision-safe rename, creates parent
# ---------------------------------------------------------------------------

def test_safe_move_basic(tmp_path):
    src = tmp_path / "a.txt"
    src.write_text("hello")
    dst = tmp_path / "sub" / "a.txt"
    final = fo.safe_move(src, dst)
    assert final == dst
    assert final.read_text() == "hello"
    assert not src.exists()             # moved, not copied


def test_safe_move_collision_never_overwrites(tmp_path):
    (tmp_path / "dst").mkdir()
    existing = tmp_path / "dst" / "a.txt"
    existing.write_text("ORIGINAL")     # must survive untouched

    src = tmp_path / "a.txt"
    src.write_text("NEW")
    final = fo.safe_move(src, tmp_path / "dst" / "a.txt")

    assert final != existing
    assert final.name == "a (1).txt"
    assert existing.read_text() == "ORIGINAL"   # never clobbered
    assert final.read_text() == "NEW"


def test_safe_move_multiple_collisions(tmp_path):
    (tmp_path / "dst").mkdir()
    (tmp_path / "dst" / "a.txt").write_text("0")
    (tmp_path / "dst" / "a (1).txt").write_text("1")
    src = tmp_path / "a.txt"
    src.write_text("2")
    final = fo.safe_move(src, tmp_path / "dst" / "a.txt")
    assert final.name == "a (2).txt"


# ---------------------------------------------------------------------------
# plan_organization() — what gets moved, what gets skipped
# ---------------------------------------------------------------------------

def _make(p: Path, age_seconds: float = 60.0) -> Path:
    """Create a file and backdate its mtime past the 'being written' guard."""
    p.write_text("x")
    past = time.time() - age_seconds
    os.utime(p, (past, past))
    return p


def test_plan_groups_by_category(tmp_path):
    _make(tmp_path / "a.jpg")
    _make(tmp_path / "b.pdf")
    plan = fo.plan_organization(tmp_path)
    dests = {m.src.name: m.dst for m in plan}
    assert dests["a.jpg"].parent.name == "Images"
    assert dests["b.pdf"].parent.name == "PDFs"
    # destinations live one level inside the organized folder
    assert all(m.dst.parent.parent == tmp_path for m in plan)


def test_plan_skips_hidden_and_system_files(tmp_path):
    for name in [".hidden", ".DS_Store", "Thumbs.db", "desktop.ini"]:
        _make(tmp_path / name)
    assert fo.plan_organization(tmp_path) == []


def test_plan_skips_partial_downloads(tmp_path):
    for name in ["big.crdownload", "file.part", "movie.mp4.download", "x.tmp"]:
        _make(tmp_path / name)
    assert fo.plan_organization(tmp_path) == []


def test_plan_skips_recently_modified(tmp_path):
    """A file written milliseconds ago may still be in flight — leave it."""
    (tmp_path / "fresh.jpg").write_text("x")   # mtime = now
    plan = fo.plan_organization(tmp_path, min_age_seconds=10.0)
    assert plan == []


def test_plan_skips_directories(tmp_path):
    (tmp_path / "somedir").mkdir()
    assert fo.plan_organization(tmp_path) == []


def test_plan_is_idempotent(tmp_path):
    """Files already sitting in their category folder are not re-moved."""
    img_dir = tmp_path / "Images"
    img_dir.mkdir()
    _make(img_dir / "a.jpg")
    # top-level category folders themselves must never be planned for a move
    assert fo.plan_organization(tmp_path) == []


# ---------------------------------------------------------------------------
# apply_plan() / organize_folder() — execution, dry-run, manifest
# ---------------------------------------------------------------------------

def test_dry_run_changes_nothing(tmp_path):
    f = _make(tmp_path / "a.jpg")
    result = fo.organize_folder(tmp_path, dry_run=True)
    assert f.exists()                          # untouched
    assert not (tmp_path / "Images").exists()
    assert len(result.moved) == 1              # reported as *would* move
    assert result.dry_run is True


def test_organize_moves_and_writes_manifest(tmp_path):
    _make(tmp_path / "a.jpg")
    _make(tmp_path / "b.pdf")
    manifest = tmp_path / ".manifest.jsonl"
    result = fo.organize_folder(tmp_path, dry_run=False, manifest_path=manifest)

    assert (tmp_path / "Images" / "a.jpg").exists()
    assert (tmp_path / "PDFs" / "b.pdf").exists()
    assert not (tmp_path / "a.jpg").exists()
    assert manifest.exists()
    assert len(result.moved) == 2


def test_undo_restores_everything(tmp_path):
    _make(tmp_path / "a.jpg")
    (tmp_path / "a.jpg").write_text("img")
    past = time.time() - 60
    os.utime(tmp_path / "a.jpg", (past, past))
    manifest = tmp_path / ".manifest.jsonl"
    fo.organize_folder(tmp_path, dry_run=False, manifest_path=manifest)
    assert not (tmp_path / "a.jpg").exists()

    undo_result = fo.undo(manifest)
    assert (tmp_path / "a.jpg").read_text() == "img"   # back home
    assert len(undo_result.restored) == 1


def test_organize_never_deletes_on_collision(tmp_path):
    """If something already occupies the destination, both files survive."""
    (tmp_path / "Images").mkdir()
    (tmp_path / "Images" / "a.jpg").write_text("EXISTING")
    _make(tmp_path / "a.jpg")
    (tmp_path / "a.jpg").write_text("INCOMING")
    past = time.time() - 60
    os.utime(tmp_path / "a.jpg", (past, past))

    fo.organize_folder(tmp_path, dry_run=False)

    contents = sorted(p.read_text() for p in (tmp_path / "Images").glob("*.jpg"))
    assert contents == ["EXISTING", "INCOMING"]   # nothing lost


def test_full_run_is_idempotent(tmp_path):
    _make(tmp_path / "a.jpg")
    fo.organize_folder(tmp_path, dry_run=False)
    second = fo.organize_folder(tmp_path, dry_run=False)
    assert second.moved == []     # nothing left to do


# ---------------------------------------------------------------------------
# default_target_folders() — the four folders the user chose
# ---------------------------------------------------------------------------

def test_default_targets_under_home():
    targets = fo.default_target_folders()
    home = Path.home()
    names = {p.name for p in targets}
    assert {"Downloads", "Desktop", "Documents"}.issubset(names)
    assert all(home in p.parents or p == home for p in targets)
