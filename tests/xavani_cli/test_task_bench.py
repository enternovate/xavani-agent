# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""End-to-end faux-mode tests for the scripts/task_bench harness.

Drives the real AIAgent loop through the faux provider transport seam
(no network, no API keys) over three tiny tasks and checks the results
JSON contract, the aggregate math, and the rendered summary.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.task_bench.run_bench import (
    BenchError,
    load_tasks,
    main,
    percentile,
    summarize_results,
)

pytestmark = pytest.mark.e2e

_TASKS = [
    {"id": "t1-hi", "prompt": "say hi", "verifier": "contains:hi"},
    {"id": "t2-ping", "prompt": "echo ping", "verifier": "contains:PING"},
    {
        "id": "t3-miss",
        "prompt": "name the animal",
        "verifier": "contains:zebra",
        "faux_response": "a horse, actually",
    },
]


def _write_tasks(tmp_path: Path) -> Path:
    tasks_path = tmp_path / "tasks.json"
    tasks_path.write_text(json.dumps(_TASKS), encoding="utf-8")
    return tasks_path


def test_load_tasks_rejects_bad_verifier(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(
        json.dumps([{"id": "x", "prompt": "p", "verifier": "regex:([unclosed"}]),
        encoding="utf-8",
    )
    with pytest.raises(BenchError):
        load_tasks(bad)


def test_load_tasks_rejects_non_list_and_duplicates(tmp_path):
    not_list = tmp_path / "not_list.json"
    not_list.write_text(json.dumps({"id": "x"}), encoding="utf-8")
    with pytest.raises(BenchError):
        load_tasks(not_list)

    dupes = tmp_path / "dupes.json"
    dupes.write_text(
        json.dumps(
            [
                {"id": "a", "prompt": "p", "verifier": "contains:a"},
                {"id": "a", "prompt": "q", "verifier": "contains:b"},
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(BenchError):
        load_tasks(dupes)


def test_percentile_interpolates():
    assert percentile([], 0.9) is None
    assert percentile([5.0], 0.9) == 5.0
    assert percentile([1.0, 2.0, 3.0, 4.0], 0.5) == 2.5
    assert percentile([10.0, 20.0, 30.0], 0.9) == 28.0


def test_faux_bench_end_to_end(tmp_path, capsys):
    tasks_path = _write_tasks(tmp_path)
    out_path = tmp_path / "results.json"

    exit_code = main(
        ["--faux", "--out", str(out_path), str(tasks_path)],
    )

    assert exit_code == 0
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["mode"] == "faux"

    results = payload["results"]
    assert len(results) == 3
    by_id = {r["id"]: r for r in results}
    assert [by_id[t["id"]]["success"] for t in _TASKS] == [True, True, False]
    for row in results:
        assert row["wall_seconds"] >= 0.0
        assert isinstance(row["total_tokens"], int)
        assert row["estimated_cost_usd"] >= 0.0
    assert by_id["t3-miss"]["error"] is None

    summary = payload["summary"]
    walls = sorted(r["wall_seconds"] for r in results)
    assert summary["task_count"] == 3
    assert summary["success_count"] == 2
    assert summary["median_wall_seconds"] == pytest.approx(walls[1])
    assert summary["success_rate"] == pytest.approx(2 / 3)
    total_cost = sum(r["estimated_cost_usd"] for r in results)
    assert summary["total_cost_usd"] == pytest.approx(total_cost)
    assert summary["cost_per_successful_task_usd"] == pytest.approx(total_cost / 2)

    rendered = capsys.readouterr().out
    for task_id in ("t1-hi", "t2-ping", "t3-miss"):
        assert task_id in rendered
    assert "median_wall_s" in rendered
    assert "cost_per_successful_task_usd" in rendered


def test_summarize_results_handles_all_failures():
    rows = [
        {"success": False, "wall_seconds": 1.0, "total_tokens": 10,
         "estimated_cost_usd": 0.5},
    ]
    summary = summarize_results(rows)
    assert summary["cost_per_successful_task_usd"] is None
    assert summary["success_rate"] == 0.0
