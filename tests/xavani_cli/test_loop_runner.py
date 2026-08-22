# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for xavani_cli/loop_runner.py."""

import pytest

from xavani_cli import loop_runner as lr


@pytest.fixture
def ldir(tmp_path, monkeypatch):
    monkeypatch.setenv("XAVANI_LOOPS_DIR", str(tmp_path / "loops"))
    return tmp_path / "loops"


def test_new_loop_rejects_empty_prompt(ldir):
    with pytest.raises(lr.LoopError):
        lr.new_loop("  ")


def test_new_loop_persists_and_loads(ldir):
    spec = lr.new_loop("do the thing", max_passes=3, directory=ldir)
    loaded = lr.load(spec["id"], directory=ldir)
    assert loaded["prompt"] == "do the thing"
    assert loaded["status"] == "active"
    assert loaded["passes"] == []


def test_new_loop_rejects_bad_conditions(ldir):
    with pytest.raises(lr.LoopError):
        lr.new_loop("x", max_passes=0, directory=ldir)
    with pytest.raises(lr.LoopError):
        lr.new_loop("x", every_seconds=0, directory=ldir)


def test_load_missing_raises(ldir):
    with pytest.raises(lr.LoopError):
        lr.load("loop-nope", directory=ldir)


def test_stop_marks_status(ldir):
    spec = lr.new_loop("x", directory=ldir)
    stopped = lr.stop(spec["id"], directory=ldir)
    assert stopped["status"] == "stopped"


def test_check_stop_conditions_max_passes():
    spec = {"passes": [{"n": i} for i in range(3)], "max_passes": 3}
    assert lr.check_stop_conditions(spec) == "max passes reached (3)"
    spec2 = {"passes": [{"n": 1}], "max_passes": 3}
    assert lr.check_stop_conditions(spec2) is None


def test_check_stop_conditions_budget_and_wall():
    spec = {"passes": [], "max_passes": 10, "budget_usd": 1.0}
    reason = lr.check_stop_conditions(spec, spent_usd=1.5)
    assert reason is not None and "budget cap" in reason
    spec2 = {"passes": [], "max_passes": 10, "wall_limit_seconds": 60}
    reason2 = lr.check_stop_conditions(spec2, elapsed_seconds=61)
    assert reason2 is not None and "wall-clock" in reason2


def test_check_stop_conditions_user_stopped():
    assert lr.check_stop_conditions({"status": "stopped", "passes": []}) == (
        "stopped by user"
    )


def test_run_loop_stops_on_success_predicate(ldir):
    spec = lr.new_loop("fix it", max_passes=10, directory=ldir)
    calls = []

    def runner(prompt, last_output, failure_notes):
        calls.append((prompt, last_output, list(failure_notes)))
        return "done" if len(calls) >= 2 else "not yet"

    result = lr.run_loop(
        spec, runner,
        success_predicate=lambda out: out == "done",
        cost_per_pass_usd=0.01, directory=ldir,
    )
    assert result["status"] == "completed"
    assert "success predicate met at pass 2" in result["stop_reason"]
    assert len(result["passes"]) == 2
    assert result["best_output"] == "done"
    # Second pass saw the first pass output.
    assert calls[1][1] == "not yet"


def test_run_loop_stops_at_max_passes(ldir):
    spec = lr.new_loop("keep going", max_passes=3, directory=ldir)

    def runner(prompt, last_output, failure_notes):
        return f"pass output {len(spec['passes']) + 1}"

    result = lr.run_loop(spec, runner, directory=ldir)
    assert result["status"] == "completed"
    assert result["stop_reason"] == "max passes reached (3)"
    assert len(result["passes"]) == 3
    # Every pass persisted to disk immediately (crash-safe).
    reloaded = lr.load(spec["id"], directory=ldir)
    assert len(reloaded["passes"]) == 3


def test_run_loop_carries_failure_notes(ldir):
    spec = lr.new_loop("iterate", max_passes=5, directory=ldir)
    lr.record_failure_note(spec, "last attempt missed the verifier",
                           directory=ldir)
    seen_notes = []

    def runner(prompt, last_output, failure_notes):
        seen_notes.append(list(failure_notes))
        return "still failing"

    lr.run_loop(spec, runner, directory=ldir)
    assert seen_notes[0] == ["last attempt missed the verifier"]


def test_record_failure_note_caps_at_limit(ldir):
    spec = lr.new_loop("x", directory=ldir)
    for i in range(lr.MAX_FAILURE_NOTES + 5):
        lr.record_failure_note(spec, f"note {i}", directory=ldir)
    assert len(spec["failure_notes"]) == lr.MAX_FAILURE_NOTES
    assert spec["failure_notes"][0] == "note 5"


def test_list_loops_sorted(ldir):
    a = lr.new_loop("first", directory=ldir)
    b = lr.new_loop("second", directory=ldir)
    names = [s["id"] for s in lr.list_loops(directory=ldir)]
    assert names == sorted([a["id"], b["id"]])


def test_summary_reports_cost_and_status(ldir):
    spec = lr.new_loop("x", max_passes=1, directory=ldir)
    result = lr.run_loop(spec, lambda **kw: "out", cost_per_pass_usd=0.25,
                         directory=ldir)
    text = lr.summary(result)
    assert "$0.2500" in text
    assert "max passes reached" in text
