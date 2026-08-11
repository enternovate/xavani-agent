# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""A16: preflight gate for long-running operations tests."""

import os
import time

import pytest

from tools.long_running import (
    PreflightError,
    check_disk_space,
    check_network,
    check_stale_locks,
    check_writable,
    preflight,
    raise_if_problems,
)

pytestmark = pytest.mark.integration


# ── writable ────────────────────────────────────────────────────────


def test_writable_ok(tmp_path):
    assert check_writable([tmp_path / "out" / "file.bin"]) == []


def test_writable_failure(tmp_path):
    ro = tmp_path / "ro"
    ro.mkdir()
    os.chmod(ro, 0o500)
    try:
        problems = check_writable([ro / "x"])
        assert problems and "not writable" in problems[0]
    finally:
        os.chmod(ro, 0o700)


# ── disk space ──────────────────────────────────────────────────────


def test_disk_space_ok(tmp_path):
    assert check_disk_space(tmp_path, 1) == []


def test_disk_space_fails_when_full(tmp_path, monkeypatch):
    class Tiny:
        free = 1024  # 1 KB

    monkeypatch.setattr("tools.long_running.shutil.disk_usage", lambda p: Tiny())
    problems = check_disk_space(tmp_path, 500)
    assert problems and "MB free" in problems[0]


# ── stale locks ─────────────────────────────────────────────────────


def test_no_lock_file_ok(tmp_path):
    assert check_stale_locks([tmp_path / "nope.lock"]) == []


def test_stale_lock_ignored(tmp_path):
    lock = tmp_path / "old.lock"
    lock.write_text("999999", encoding="utf-8")  # dead pid
    old = time.time() - 3600
    os.utime(lock, (old, old))
    assert check_stale_locks([lock], stale_after_s=300) == []


def test_live_lock_blocked(tmp_path):
    lock = tmp_path / "live.lock"
    lock.write_text(str(os.getpid()), encoding="utf-8")  # this process
    problems = check_stale_locks([lock], stale_after_s=300)
    assert problems and "live pid" in problems[0]


def test_fresh_lock_without_pid_blocked(tmp_path):
    lock = tmp_path / "fresh.lock"
    lock.write_text("not-a-pid", encoding="utf-8")
    problems = check_stale_locks([lock], stale_after_s=300)
    assert problems and "no pid" in problems[0]


# ── network ─────────────────────────────────────────────────────────


def test_network_unreachable_reports_problem(monkeypatch):
    def boom(addr, timeout):
        raise OSError("connection refused")

    monkeypatch.setattr("tools.long_running.socket.create_connection", boom)
    problems = check_network("example.com", 443)
    assert problems and "unreachable" in problems[0]


def test_network_ok(monkeypatch):
    from contextlib import nullcontext

    monkeypatch.setattr(
        "tools.long_running.socket.create_connection",
        lambda addr, timeout: nullcontext(),
    )
    assert check_network("example.com", 443) == []


# ── preflight aggregate ─────────────────────────────────────────────


def test_preflight_all_ok(tmp_path):
    results = preflight(
        writable_paths=[tmp_path / "out"],
        disk_path=tmp_path,
        lock_paths=[tmp_path / "no.lock"],
    )
    assert results == {}


def test_preflight_collects_multiple_problems(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.long_running.shutil.disk_usage",
                        lambda p: type("T", (), {"free": 1024})())
    lock = tmp_path / "live.lock"
    lock.write_text(str(os.getpid()), encoding="utf-8")
    results = preflight(
        writable_paths=[tmp_path / "out"],
        disk_path=tmp_path,
        disk_min_mb=500,
        lock_paths=[lock],
    )
    assert "disk" in results
    assert "locks" in results
    assert "writable" not in results


def test_raise_if_problems_ok():
    raise_if_problems({})  # must not raise


def test_raise_if_problems_raises():
    with pytest.raises(PreflightError) as ei:
        raise_if_problems({"disk": ["/tmp has 0 MB free"]})
    assert "Preflight failed" in str(ei.value)
    assert "/tmp has 0 MB free" in str(ei.value)


def test_preflight_network_flag(monkeypatch):
    monkeypatch.setattr(
        "tools.long_running.socket.create_connection",
        lambda addr, timeout: (_ for _ in ()).throw(OSError("refused")),
    )
    results = preflight(check_network_host="api.anthropic.com")
    assert "network" in results
