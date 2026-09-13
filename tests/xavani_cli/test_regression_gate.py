# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the bench regression gate."""

import json

import pytest

from scripts.task_bench.regression_gate import load_metrics, main, worsened


def _write(tmp_path, name, summary):
    path = tmp_path / name
    path.write_text(json.dumps({"summary": summary}), encoding="utf-8")
    return path


def test_main_blocks_success_regression_despite_faster_cheaper_run(tmp_path, capsys):
    base = _write(tmp_path, "base.json", {
        "median_wall_s": 80.0, "cost_per_successful_task_usd": 0.02,
        "success_rate": 1.0,
    })
    current = _write(tmp_path, "current.json", {
        "median_wall_s": 40.0, "cost_per_successful_task_usd": 0.01,
        "success_rate": 0.99,
    })

    assert main([str(base), str(current)]) == 1
    assert "success_rate" in capsys.readouterr().out.split("REGRESSION GATE FAILED:")[1]


@pytest.fixture
def valid_summary():
    return {
        "median_wall_s": 80.0,
        "cost_per_successful_task_usd": 0.02,
        "success_rate": 0.9,
    }


@pytest.mark.parametrize("side", ["base", "current"])
@pytest.mark.parametrize("success", [
    {}, {"success_rate": None}, {"success_rate": True}, {"success_rate": False},
    {"success_rate": "0.9"}, {"success_rate": "invalid"}, {"success_rate": []},
    {"success_rate": {}}, {"success_rate": float("nan")},
    {"success_rate": float("inf")}, {"success_rate": float("-inf")},
    {"success_rate": -0.1}, {"success_rate": 1.1},
])
def test_main_rejects_invalid_success_rate(tmp_path, capsys, valid_summary, side, success):
    invalid = {key: value for key, value in valid_summary.items() if key != "success_rate"}
    invalid.update(success)
    paths = [
        _write(tmp_path, f"{name}.json", invalid if name == side else valid_summary)
        for name in ("base", "current")
    ]

    assert main([str(path) for path in paths]) == 2
    captured = capsys.readouterr()
    assert "success_rate" in captured.err
    assert "Regression gate passed" not in captured.out


@pytest.mark.parametrize("side", ["base", "current"])
@pytest.mark.parametrize("key", ["median_wall_s", "cost_per_successful_task_usd"])
@pytest.mark.parametrize("value", [
    "missing", None, True, False, "0.1", "invalid", [], {},
    float("nan"), float("inf"), float("-inf"), -0.1, 10 ** 400,
])
def test_main_rejects_invalid_measurements(tmp_path, capsys, valid_summary, side, key, value):
    invalid = {**valid_summary, key: value}
    if value == "missing":
        invalid.pop(key)
    paths = [
        _write(tmp_path, f"{name}.json", invalid if name == side else valid_summary)
        for name in ("base", "current")
    ]

    assert main([str(path) for path in paths]) == 2
    captured = capsys.readouterr()
    assert key in captured.err
    assert "Regression gate passed" not in captured.out


@pytest.mark.parametrize("side", ["base", "current"])
@pytest.mark.parametrize("document", [
    "{", "", "[]", "null", "true", "1", '"text"', "{}",
    '{"summary": null}', '{"summary": []}', '{"summary": true}',
    '{"summary": 1}', '{"summary": "text"}', '{"summary": {}}',
])
def test_main_rejects_malformed_results(tmp_path, capsys, valid_summary, side, document):
    paths = {name: _write(tmp_path, f"{name}.json", valid_summary)
             for name in ("base", "current")}
    paths[side].write_text(document, encoding="utf-8")

    assert main([str(paths["base"]), str(paths["current"])]) == 2
    captured = capsys.readouterr()
    assert "Invalid benchmark input" in captured.err
    assert "Regression gate passed" not in captured.out


@pytest.mark.parametrize("tolerance", ["nan", "inf", "-inf", "-0.1", "invalid", "1e400"])
def test_main_rejects_invalid_tolerance(tmp_path, capsys, valid_summary, tolerance):
    base = _write(tmp_path, "base.json", valid_summary)
    current = _write(tmp_path, "current.json", valid_summary)

    assert main([str(base), str(current), f"--tolerance={tolerance}"]) == 2
    captured = capsys.readouterr()
    assert "tolerance" in captured.err
    assert "Regression gate passed" not in captured.out


@pytest.mark.parametrize("side", ["base", "current"])
@pytest.mark.parametrize("kind", ["missing", "directory", "invalid-utf8"])
def test_main_rejects_unreadable_input(tmp_path, capsys, valid_summary, side, kind):
    paths = {name: _write(tmp_path, f"{name}.json", valid_summary)
             for name in ("base", "current")}
    paths[side].unlink()
    if kind == "directory":
        paths[side].mkdir()
    elif kind == "invalid-utf8":
        paths[side].write_bytes(b"\xff")

    assert main([str(paths["base"]), str(paths["current"])]) == 2
    captured = capsys.readouterr()
    assert "Invalid benchmark input" in captured.err
    assert "Regression gate passed" not in captured.out


@pytest.mark.parametrize("flat", [False, True])
@pytest.mark.parametrize("baseline_success,current_success", [
    (0, 0), (0, 1), (0.9, 0.9), (0.9, 1), (1, 1),
])
def test_main_accepts_equal_or_improved_success(
    tmp_path, capsys, valid_summary, flat, baseline_success, current_success,
):
    paths = []
    for name, success in (("base", baseline_success), ("current", current_success)):
        summary = {**valid_summary, "success_rate": success}
        path = _write(tmp_path, f"{name}.json", summary)
        if flat:
            path.write_text(json.dumps(summary), encoding="utf-8")
        paths.append(str(path))

    assert main(paths) == 0
    assert "Regression gate passed" in capsys.readouterr().out


@pytest.mark.parametrize("key", ["median_wall_s", "cost_per_successful_task_usd"])
@pytest.mark.parametrize("baseline,current,tolerance,expected", [
    (100, 110, "0.10", 0), (100, 111, "0.10", 1),
    (100, 100, "0", 0), (100, 101, "0", 1),
    (0, 0, "0.10", 0), (0, 100, "0.10", 0),
])
def test_main_preserves_measurement_tolerance(
    tmp_path, valid_summary, key, baseline, current, tolerance, expected,
):
    base = _write(tmp_path, "base.json", {**valid_summary, key: baseline})
    cur = _write(tmp_path, "current.json", {
        **valid_summary, key: current, "success_rate": 1,
    })

    assert main([str(base), str(cur), "--tolerance", tolerance]) == expected


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
