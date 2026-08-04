# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""E10: performance regression detector tests."""

import json

from scripts.benchmark import (
    compare,
    load_baseline,
    _p95,
    store_baseline,
)


# ── p95 percentile ──────────────────────────────────────────────────


def test_p95_single_value():
    assert _p95([42.0]) == 42.0


def test_p95_sorted_input():
    values = [10.0, 20.0, 30.0, 40.0]
    # idx = 0.95*3 = 2.85 -> interpolate between 30 and 40.
    assert _p95(values) == 38.5


def test_p95_empty():
    assert _p95([]) == 0.0


# ── compare against baseline ────────────────────────────────────────


def test_no_regression_passes():
    results = {"import_tools": 10.0}
    baseline = {"import_tools": 10.0}
    assert compare(results, baseline, 0.20) == []


def test_small_drift_passes():
    results = {"import_tools": 11.5}  # +15%
    baseline = {"import_tools": 10.0}
    assert compare(results, baseline, 0.20) == []


def test_regression_fails():
    results = {"import_tools": 13.0}  # +30%
    baseline = {"import_tools": 10.0}
    problems = compare(results, baseline, 0.20)
    assert len(problems) == 1
    assert "import_tools" in problems[0]
    assert "+30%" in problems[0]


def test_missing_baseline_skipped():
    results = {"import_tools": 100.0}
    assert compare(results, {}, 0.20) == []


def test_new_benchmark_skipped():
    results = {"import_tools": 10.0, "new_bench": 5.0}
    baseline = {"import_tools": 10.0}
    problems = compare(results, baseline, 0.20)
    assert all("new_bench" not in p for p in problems)


def test_zero_baseline_skipped():
    results = {"import_tools": 10.0}
    baseline = {"import_tools": 0.0}
    assert compare(results, baseline, 0.20) == []


# ── baseline persistence ────────────────────────────────────────────


def test_store_and_load_baseline(tmp_path, monkeypatch):
    import scripts.benchmark as bench

    target = tmp_path / "baseline.json"
    monkeypatch.setattr(bench, "BASELINE_FILE", target)
    store_baseline({"import_tools": 1.5, "config_load": 80.0})
    assert load_baseline() == {"import_tools": 1.5, "config_load": 80.0}


def test_load_missing_baseline_returns_empty(tmp_path, monkeypatch):
    import scripts.benchmark as bench

    monkeypatch.setattr(bench, "BASELINE_FILE", tmp_path / "nope.json")
    assert load_baseline() == {}


def test_committed_baseline_is_valid_json():
    """The checked-in baseline must parse and contain our benchmarks."""
    from pathlib import Path

    baseline_file = Path("scripts/benchmark-baseline.json")
    assert baseline_file.exists(), "run scripts/benchmark.py --update-baseline"
    data = json.loads(baseline_file.read_text(encoding="utf-8"))
    assert "import_tools" in data
    assert "config_load" in data
