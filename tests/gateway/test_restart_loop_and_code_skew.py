# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""A08/A09: code-skew detection + restart-loop breaker tests."""

import json
import time

import pytest

from gateway import code_skew
from gateway import restart_loop_guard as rlg
from xavani_constants import get_xavani_home


@pytest.fixture(autouse=True)
def _fresh_state(monkeypatch, tmp_path):
    """Isolate the state file in a temp home and reset module state."""
    monkeypatch.setenv("XAVANI_HOME", str(tmp_path))
    monkeypatch.setattr(code_skew, "_boot_fingerprint", None)
    monkeypatch.setattr(code_skew, "_skew_warned", False)
    rlg.reset_breaker()
    yield
    rlg.reset_breaker()


# ── A08 code skew ─────────────────────────────────────────────────────


def test_record_boot_fingerprint_idempotent():
    code_skew.record_boot_fingerprint()
    first = code_skew._boot_fingerprint
    code_skew.record_boot_fingerprint()
    assert code_skew._boot_fingerprint == first


def test_no_skew_without_boot_snapshot():
    assert code_skew.detect_code_skew() is None


def test_detect_skew_after_drift(monkeypatch):
    code_skew.record_boot_fingerprint()
    monkeypatch.setattr(
        code_skew, "_fingerprint", lambda: "git:main:0123456789abcdef0123456789abcdef01234567"
    )
    skew = code_skew.detect_code_skew()
    assert skew is not None
    boot, disk = skew
    assert disk == "0123456789"


def test_warn_once_per_boot(monkeypatch, caplog):
    code_skew.record_boot_fingerprint()
    monkeypatch.setattr(
        code_skew, "_fingerprint", lambda: "git:main:0123456789abcdef0123456789abcdef01234567"
    )
    assert code_skew.warn_if_code_skew() is True
    assert code_skew.warn_if_code_skew() is False  # warned already


def test_fingerprint_handles_git_failure(monkeypatch):
    monkeypatch.setattr(code_skew, "_git", lambda args: "")
    assert code_skew._fingerprint() is None


# ── A09 restart loop guard ────────────────────────────────────────────


def test_single_boot_not_tripped():
    rlg.record_boot()
    assert rlg.restart_loop_tripped() is False


def test_many_boots_trip_breaker():
    for _ in range(rlg.DEFAULT_MAX_RESTARTS):
        rlg.record_boot()
    assert rlg.restart_loop_tripped() is True


def test_window_expiry_clears_trip(monkeypatch):
    now = time.time()
    timestamps = [now - (i * 10) for i in range(rlg.DEFAULT_MAX_RESTARTS)]
    state = get_xavani_home() / "gateway" / "restart_loop.json"
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(json.dumps({"boots": timestamps}), encoding="utf-8")
    # All boots are within the window -> tripped.
    assert rlg.restart_loop_tripped() is True
    # Old boots fall out of the window.
    state.write_text(
        json.dumps({"boots": [now - rlg.DEFAULT_WINDOW_SECONDS - 60]}),
        encoding="utf-8",
    )
    assert rlg.restart_loop_tripped() is False


def test_state_failure_fails_open(monkeypatch, tmp_path):
    from pathlib import Path

    monkeypatch.setattr(
        rlg, "_state_path", lambda: Path("/nonexistent-dir-xavani/restart.json")
    )
    rlg.record_boot()  # must not raise
    assert rlg.restart_loop_tripped() is False


def test_reset_breaker_clears_window():
    for _ in range(rlg.DEFAULT_MAX_RESTARTS):
        rlg.record_boot()
    assert rlg.restart_loop_tripped() is True
    rlg.reset_breaker()
    assert rlg.restart_loop_tripped() is False
