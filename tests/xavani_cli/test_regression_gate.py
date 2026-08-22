# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the bench regression gate."""

import json

import pytest

from scripts.task_bench.regression_gate import load_metrics, worsened


def _write(tmp_path, name, summary):
    path = tmp_path / name
    path.write_text(json.dumps({"summary": summary}), encoding="utf-8")
    return path


def test_load_metrics_reads_summary(tmp_path):
    path = _write(tmp_path, "r.json", {
        "median_wall_s": 0.5, "cost_per_successful_task_usd": 0.01,
        "success_rate": 1.0,
    })
    metrics = load_metrics(path)
    assert metrics["median_wall_s"] == 0.5
    assert metrics["cost_per_successful_task_usd"] == 0.01


def test_worsened_detects_median_increase():
    assert worsened(0.5, 0.6, tolerance=0.10) is True
    assert worsened(0.5, 0.54, tolerance=0.10) is False


def test_worsened_handles_zero_and_none():
    assert worsened(0, 100, tolerance=0.10) is False
    assert worsened(None, 100, tolerance=0.10) is False
    assert worsened(0.5, None, tolerance=0.10) is False


def test_gate_end_to_end_pass_and_fail(tmp_path, capsys):
    from scripts.task_bench import regression_gate

    base = _write(tmp_path, "base.json", {
        "median_wall_s": 80.0, "cost_per_successful_task_usd": 0.02,
        "success_rate": 1.0,
    })
    good = _write(tmp_path, "good.json", {
        "median_wall_s": 85.0, "cost_per_successful_task_usd": 0.02,
        "success_rate": 1.0,
    })
    bad = _write(tmp_path, "bad.json", {
        "median_wall_s": 95.0, "cost_per_successful_task_usd": 0.02,
        "success_rate": 1.0,
    })

    assert regression_gate.main([str(base), str(good)]) == 0
    assert regression_gate.main([str(base), str(bad)]) == 1
