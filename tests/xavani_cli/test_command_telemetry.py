# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""D02: dangerous-command telemetry tests."""

import json
import time

import pytest

import xavani_cli.command_telemetry as ct
from xavani_cli.command_telemetry import (
    format_telemetry_report,
    load_entries,
    telemetry_report,
)


@pytest.fixture(autouse=True)
def _isolated_log(tmp_path, monkeypatch):
    log = tmp_path / "approval_reasoning.jsonl"
    monkeypatch.setattr(ct, "_reason_log_path", lambda: log)
    yield log
    try:
        log.unlink(missing_ok=True)
    except OSError:
        pass


def _write(log, decision="deny", reason="hardline", pattern="rm_root", ts=None):
    record = {
        "ts": ts if ts is not None else time.time(),
        "decision": decision,
        "reason": reason,
        "pattern_key": pattern,
        "command": "rm -rf /",
        "session_key": "s1",
    }
    with open(log, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


# ── loading ─────────────────────────────────────────────────────────


def test_load_empty(_isolated_log):
    assert load_entries() == []


def test_load_filters_by_window(_isolated_log):
    _write(_isolated_log, ts=time.time() - 48 * 3600)  # 2 days old
    assert load_entries(hours=24) == []
    assert len(load_entries(hours=72)) == 1


def test_load_skips_corrupt_lines(_isolated_log):
    _isolated_log.write_text("not json\n", encoding="utf-8")
    _write(_isolated_log)
    assert len(load_entries()) == 1


# ── aggregation ─────────────────────────────────────────────────────


def test_report_counts_decisions(_isolated_log):
    _write(_isolated_log, decision="deny", reason="hardline")
    _write(_isolated_log, decision="deny", reason="hardline")
    _write(_isolated_log, decision="allow", reason="yolo")
    report = telemetry_report()
    assert report["total_decisions"] == 3
    assert report["decisions"] == {"deny": 2, "allow": 1}
    assert report["deny_rate"] == pytest.approx(2 / 3, abs=1e-3)
    assert report["allow_rate"] == pytest.approx(1 / 3, abs=1e-3)


def test_report_top_reasons(_isolated_log):
    for _ in range(3):
        _write(_isolated_log, reason="hardline")
    _write(_isolated_log, reason="user")
    report = telemetry_report()
    assert report["top_reasons"]["hardline"] == 3
    assert report["top_reasons"]["user"] == 1


def test_report_top_patterns(_isolated_log):
    for _ in range(4):
        _write(_isolated_log, pattern="rm_root")
    report = telemetry_report()
    assert report["top_patterns"]["rm_root"] == 4


def test_report_by_reason_breakdown(_isolated_log):
    _write(_isolated_log, decision="deny", reason="hardline")
    _write(_isolated_log, decision="allow", reason="hardline")
    report = telemetry_report()
    breakdown = report["by_reason"]["hardline"]
    assert breakdown["deny"] == 1 and breakdown["allow"] == 1


def test_report_empty(_isolated_log):
    report = telemetry_report()
    assert report["total_decisions"] == 0
    assert report["deny_rate"] == 0.0
    assert report["top_reasons"] == {}
    assert report["top_patterns"] == {}


# ── formatting ─────────────────────────────────────────────────────


def test_format_report(_isolated_log):
    _write(_isolated_log, decision="deny", reason="hardline")
    block = format_telemetry_report(telemetry_report())
    assert "deny rate" in block
    assert "hardline" in block


def test_format_empty_report(_isolated_log):
    block = format_telemetry_report(telemetry_report())
    assert "0 decisions" in block
