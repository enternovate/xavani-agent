# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.


"""E06: flake dashboard report tests."""

from __future__ import annotations

import json

from scripts.flake_dashboard import build_report, load_entries

_SAMPLE = [
    {
        "test_id": "tests/a.py::test_one",
        "category": "assertion_error",
        "label": "root_cause=assertion_error",
        "timestamp": "2026-08-04T09:01:22Z",
        "exception_type": "AssertionError",
    },
    {
        "test_id": "tests/a.py::test_one",
        "category": "timeout",
        "label": "root_cause=timeout",
        "timestamp": "2026-08-04T09:02:00Z",
        "exception_type": "TimeoutError",
    },
    {
        "test_id": "tests/b.py::test_two",
        "category": "assertion_error",
        "label": "root_cause=assertion_error",
        "timestamp": "2026-08-04T09:03:00Z",
        "exception_type": "AssertionError",
    },
]


def test_load_entries_handles_list_and_wrapper(tmp_path):
    p = tmp_path / "flakiness.json"
    p.write_text(json.dumps(_SAMPLE), encoding="utf-8")
    assert len(load_entries(str(p))) == 3
    p.write_text(json.dumps({"entries": _SAMPLE}), encoding="utf-8")
    assert len(load_entries(str(p))) == 3


def test_build_report_ranks_by_failure_count():
    report = build_report(_SAMPLE)
    lines = report.splitlines()
    idx_one = next(i for i, l in enumerate(lines) if "tests/a.py::test_one" in l)
    idx_two = next(i for i, l in enumerate(lines) if "tests/b.py::test_two" in l)
    assert idx_one < idx_two  # 2 failures rank above 1
    assert "root_cause=assertion_error: 2" in report
    assert "root_cause=timeout: 1" in report
    assert "assertion_error: 2" in report
    assert "Total recorded failures: **3**" in report


def test_build_report_top_n():
    report = build_report(_SAMPLE, top=1)
    assert "tests/b.py::test_two" not in report
