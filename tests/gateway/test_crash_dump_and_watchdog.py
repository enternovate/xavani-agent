# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""E03/E04: crash dump writer + disk/log watchdog tests."""

import os
from pathlib import Path

import pytest

from gateway import memory_monitor
from gateway.shutdown_forensics import write_crash_dump


@pytest.fixture(autouse=True)
def _home(monkeypatch, tmp_path):
    monkeypatch.setenv("XAVANI_HOME", str(tmp_path))
    return tmp_path


# ── E03 crash dump ────────────────────────────────────────────────────


def test_write_crash_dump_creates_file(tmp_path):
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "gateway.log").write_text(
        "line1\nline2\nline3\n", encoding="utf-8"
    )
    dump = write_crash_dump("test crash", log_file=tmp_path / "logs" / "gateway.log")
    assert dump is not None
    path = Path(dump)
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "test crash" in text
    assert "line3" in text  # log tail captured
    assert "thread stacks" in text


def test_write_crash_dump_never_raises(tmp_path):
    monkeypatch_dump = pytest.MonkeyPatch()
    monkeypatch_dump.setattr(
        "gateway.shutdown_forensics.snapshot_shutdown_context",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    try:
        dump = write_crash_dump("boom case")
        # Either a dump (without context) or None — but never a raise.
        if dump is not None:
            assert Path(dump).exists()
    finally:
        monkeypatch_dump.undo()


# ── E04 disk + log rotation ───────────────────────────────────────────


def test_log_rotation_removes_oldest_when_over_500mb(tmp_path):
    logs = tmp_path / "logs"
    logs.mkdir()
    big = logs / "big.log"
    big.write_bytes(b"x" * (600 * 1024 * 1024))
    old = logs / "old.log"
    old.write_text("old", encoding="utf-8")
    import time as _time

    old_mtime = _time.time() - 3600
    os.utime(old, (old_mtime, old_mtime))

    memory_monitor._check_disk_and_logs()
    # Total log size must drop back under the 500MB budget.
    total = sum(
        p.stat().st_size
        for p in logs.iterdir()
        if p.is_file() and p.suffix == ".log"
    )
    assert total < 500 * 1024 * 1024


def test_log_rotation_skips_small_logs(tmp_path):
    logs = tmp_path / "logs"
    logs.mkdir()
    small = logs / "small.log"
    small.write_text("tiny", encoding="utf-8")
    memory_monitor._check_disk_and_logs()
    assert small.exists()


def test_disk_check_handles_missing_logs_dir(tmp_path):
    memory_monitor._check_disk_and_logs()  # no logs dir — must not raise
