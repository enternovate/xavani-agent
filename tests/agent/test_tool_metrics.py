# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for agent/tool_metrics.py — tool-call quality metrics (harness item 2)."""

from __future__ import annotations

import csv
import json

import pytest

from agent.tool_metrics import (
    ToolCallRecord,
    aggregate,
    format_stats,
    load_session,
    record_call,
)


@pytest.fixture(autouse=True)
def _tmp_metrics(tmp_path, monkeypatch):
    """Redirect metrics storage to a temp dir."""
    monkeypatch.setattr("agent.tool_metrics._metrics_dir", lambda: tmp_path)
    return tmp_path


def _rec(tool: str, ok: bool, latency: float, retries: int = 0, session: str = "s1") -> ToolCallRecord:
    return ToolCallRecord(
        tool=tool,
        started_at=0.0,
        latency_ms=latency,
        success=ok,
        retries=retries,
        error_class="" if ok else "RuntimeError",
        session_id=session,
    )


def test_record_appends_jsonl_and_csv(tmp_path) -> None:
    record_call(_rec("bash", True, 12.5, session="abc"))
    record_call(_rec("bash", False, 40.0, retries=1, session="abc"))

    jsonl = (tmp_path / "tool-calls-abc.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(jsonl) == 2
    assert json.loads(jsonl[0])["tool"] == "bash"

    csv_path = tmp_path / "tool-calls-abc.csv"
    with csv_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 2
    assert rows[0]["tool"] == "bash"
    assert rows[0]["success"] == "True"


def test_load_session_returns_records(tmp_path) -> None:
    record_call(_rec("web_fetch", True, 3.0, session="xyz"))
    calls = load_session("xyz")
    assert len(calls) == 1
    assert calls[0].tool == "web_fetch"
    assert calls[0].success is True


def test_load_session_missing_returns_empty(tmp_path) -> None:
    assert load_session("does-not-exist") == []


def test_load_session_skips_corrupt_lines(tmp_path) -> None:
    (tmp_path / "tool-calls-s1.jsonl").write_text("{not json}\n", encoding="utf-8")
    assert load_session("s1") == []


def test_aggregate_success_rate_and_latency() -> None:
    calls = [
        _rec("bash", True, 10.0),
        _rec("bash", True, 20.0),
        _rec("bash", False, 30.0),
        _rec("read_file", True, 5.0),
    ]
    agg = aggregate(calls)
    assert agg["total_calls"] == 4
    assert agg["total_success"] == 3
    bash = next(r for r in agg["per_tool"] if r["tool"] == "bash")
    assert bash["calls"] == 3
    assert bash["success_rate"] == pytest.approx(round(2 / 3, 4))
    assert bash["avg_latency_ms"] == pytest.approx(20.0)


def test_aggregate_counts_retries() -> None:
    calls = [_rec("bash", True, 1.0, retries=2), _rec("bash", True, 1.0)]
    agg = aggregate(calls)
    assert agg["total_retries"] == 2


def test_format_stats_renders_block() -> None:
    text = format_stats([_rec("bash", True, 10.0), _rec("read_file", True, 2.0)])
    assert "Tool calls: 2" in text
    assert "bash" in text
    assert "100.0% ok" in text
