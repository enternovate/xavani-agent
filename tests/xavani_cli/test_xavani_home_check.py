# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""A18: XAVANI_HOME filesystem validation.

Checks the home is writable, has free space, supports file locking, and
is not on a network filesystem. Every check is a real probe — no stat
guessing.
"""

import os
import sys
from pathlib import Path

import pytest

import xavani_home_check as hc
from xavani_home_check import (
    check_xavani_home,
    clear_home_check_cache,
    home_check_enabled,
    report_home_problems,
)

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _clean_cache():
    clear_home_check_cache()
    yield
    clear_home_check_cache()


# ── healthy home ─────────────────────────────────────────────────────


def test_healthy_tmp_home_passes(tmp_path):
    problems = check_xavani_home(tmp_path)
    assert problems == []


def test_missing_home_is_created(tmp_path):
    target = tmp_path / "nested" / "home"
    problems = check_xavani_home(target)
    assert problems == []
    assert target.is_dir()


# ── writability ──────────────────────────────────────────────────────


def test_readonly_home_reports_not_writable(tmp_path, monkeypatch):
    target = tmp_path / "ro"
    target.mkdir()
    os.chmod(target, 0o500)
    try:
        problems = check_xavani_home(target)
    finally:
        os.chmod(target, 0o700)
    assert any("not writable" in p for p in problems)


# ── free space ───────────────────────────────────────────────────────


def test_free_space_reported_when_below_minimum(tmp_path, monkeypatch):
    class TinyUsage:
        free = 1024  # 1 KB — far below the 50 MB minimum

    monkeypatch.setattr(hc.shutil, "disk_usage", lambda p: TinyUsage())
    problems = check_xavani_home(tmp_path)
    assert any("MB free" in p for p in problems)


def test_healthy_disk_usage_no_problem(tmp_path, monkeypatch):
    class BigUsage:
        free = 10 * 1024 * 1024 * 1024  # 10 GB

    monkeypatch.setattr(hc.shutil, "disk_usage", lambda p: BigUsage())
    problems = check_xavani_home(tmp_path)
    assert not any("MB free" in p for p in problems)


# ── filesystem type / locking ────────────────────────────────────────


def test_network_fs_reported(tmp_path, monkeypatch):
    monkeypatch.setattr(hc, "_fs_type", lambda p: "nfs")
    problems = check_xavani_home(tmp_path)
    assert any("nfs" in p and "locking" in p for p in problems)


def test_local_fs_with_locking_passes(tmp_path, monkeypatch):
    monkeypatch.setattr(hc, "_fs_type", lambda p: "apfs")
    monkeypatch.setattr(hc, "_lockable", lambda p: True)
    problems = check_xavani_home(tmp_path)
    assert problems == []


def test_unlockable_fs_reports(tmp_path, monkeypatch):
    monkeypatch.setattr(hc, "_fs_type", lambda p: "apfs")
    monkeypatch.setattr(hc, "_lockable", lambda p: False)
    problems = check_xavani_home(tmp_path)
    assert any("file locking" in p for p in problems)


def test_lock_probe_is_real(tmp_path):
    # A real tmpdir must be lockable with flock on POSIX.
    if sys.platform == "win32":
        pytest.skip("flock is POSIX-only")
    assert hc._lockable(tmp_path) is True


def test_fs_type_longest_prefix_wins(monkeypatch):
    """A nested mount (e.g. /home/user on nfs) overrides the root type."""
    monkeypatch.setattr(
        hc,
        "_load_mount_table",
        lambda: (("/", "apfs"), ("/Users", "nfs")),
    )
    assert hc._fs_type(Path("/Users/alice/.xavani")) == "nfs"
    # A path outside /Users resolves to the root mount type.
    assert hc._fs_type(Path("/private/tmp/x")) == "apfs"


# ── env switch ───────────────────────────────────────────────────────


def test_home_check_enabled_by_default(monkeypatch):
    monkeypatch.delenv("XAVANI_SKIP_HOME_CHECK", raising=False)
    assert home_check_enabled() is True


def test_home_check_disabled_by_env(monkeypatch):
    monkeypatch.setenv("XAVANI_SKIP_HOME_CHECK", "1")
    assert home_check_enabled() is False


def test_report_prints_problems_to_stderr(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(hc, "_fs_type", lambda p: "nfs")
    problems = report_home_problems(tmp_path)
    assert problems  # the nfs problem is reported
    err = capsys.readouterr().err
    assert "xavani home" in err


def test_report_silent_when_disabled(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("XAVANI_SKIP_HOME_CHECK", "1")
    problems = report_home_problems(tmp_path)
    assert problems == []
    assert capsys.readouterr().err == ""


def test_report_silent_when_healthy(tmp_path, capsys):
    problems = report_home_problems(tmp_path)
    assert problems == []
    assert capsys.readouterr().err == ""


# ── result caching ───────────────────────────────────────────────────


def test_check_cached_per_path(tmp_path, monkeypatch):
    calls = {"n": 0}
    real = hc._writable

    def counting(path):
        calls["n"] += 1
        return real(path)

    monkeypatch.setattr(hc, "_writable", counting)
    check_xavani_home(tmp_path)
    check_xavani_home(tmp_path)
    assert calls["n"] == 1  # second call hits the cache


# ── entry-point wiring (no side effects at import) ───────────────────


def test_xavani_entry_runs_probe_in_main_not_at_import():
    """The probe call must live inside main(), never at module scope."""
    import inspect
    import xavani

    src = inspect.getsource(xavani)
    main_src = inspect.getsource(xavani.main)
    assert "report_home_problems" in main_src
    # Module-level code (before `def main`) must not call the probe.
    module_head = src.split("def main")[0]
    assert "report_home_problems(" not in module_head


def test_cli_entry_runs_probe_in_main():
    import inspect

    from cli import main as cli_main

    main_src = inspect.getsource(cli_main)
    assert "report_home_problems" in main_src
