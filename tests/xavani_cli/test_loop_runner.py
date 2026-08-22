# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for xavani_cli/loop_runner.py."""

import json

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


def test_run_loop_detects_runaway_identical_passes(ldir):
    spec = lr.new_loop("stuck task", max_passes=10, directory=ldir)
    result = lr.run_loop(spec, lambda **kw: "same output", directory=ldir)
    assert result["status"] == "completed"
    assert "runaway detected" in result["stop_reason"]
    assert len(result["passes"]) == 3


def test_nested_loop_creation_beyond_depth_2_rejected(ldir):
    spec = lr.new_loop("outer", max_passes=1, directory=ldir)

    def runner(prompt, last_output, failure_notes):
        # Depth 1 inside the running outer loop: a depth-2 child is allowed.
        inner = lr.new_loop("inner", max_passes=1, directory=ldir)
        assert inner["prompt"] == "inner"
        # At depth 2: creating another child is rejected.
        token = lr._loop_depth.set(lr._loop_depth.get() + 1)
        try:
            with pytest.raises(lr.LoopError):
                lr.new_loop("grandchild", directory=ldir)
        finally:
            lr._loop_depth.reset(token)
        return "ok"

    lr.run_loop(spec, runner, directory=ldir)


def test_run_loop_eval_scores_and_threshold(ldir):
    spec = lr.new_loop("improve answer", max_passes=5, directory=ldir)

    def runner(prompt, last_output, failure_notes):
        n = len(spec["passes"]) + 1
        return "answer quality " + ("x" * n)

    def score_fn(out):
        return len(out) / 20.0

    result = lr.run_loop_eval(
        spec, runner, score_fn, threshold=0.8, directory=ldir,
    )
    assert result["status"] == "completed"
    assert "success predicate met" in result["stop_reason"]
    scores = [p["score"] for p in result["passes"]]
    assert scores[-1] >= 0.8
    assert all(s is not None for s in scores)
    reloaded = lr.load(spec["id"], directory=ldir)
    assert reloaded["passes"][-1]["score"] == scores[-1]


def test_run_loop_eval_tolerates_scoring_error(ldir):
    spec = lr.new_loop("y", max_passes=1, directory=ldir)

    def bad_score(out):
        raise ValueError("no rubric")

    result = lr.run_loop_eval(
        spec, lambda **kw: "out", bad_score, threshold=0.5, directory=ldir,
    )
    assert result["passes"][0]["score"] is None


def test_load_rubric_reads_and_filters(ldir, tmp_path):
    rubric = tmp_path / "rubric.txt"
    rubric.write_text(
        "# comment line\n"
        "contains:hello\n"
        "\n"
        "regex:\\d+\n",
        encoding="utf-8",
    )
    checks = lr.load_rubric(str(rubric))
    assert checks == ["contains:hello", "regex:\\d+"]


def test_load_rubric_rejects_empty(tmp_path):
    rubric = tmp_path / "empty.txt"
    rubric.write_text("# only comments\n", encoding="utf-8")
    with pytest.raises(lr.LoopError):
        lr.load_rubric(str(rubric))


def test_rubric_score_fraction():
    checks = ["contains:hello", "regex:\\d+", "contains:missing-token"]
    assert lr.rubric_score("hello world 42", checks) == pytest.approx(2 / 3)
    assert lr.rubric_score("nothing here", checks) == 0.0
    assert lr.rubric_score("hello 7 missing-token", checks) == 1.0


def test_prune_removes_old_finished_loops_only(ldir):
    import time as _time

    old_done = lr.new_loop("old done", max_passes=1, directory=ldir)
    lr.run_loop(old_done, lambda **kw: "out", directory=ldir)
    old_done_path = ldir / f"{old_done['id']}.json"
    spec = json.loads(old_done_path.read_text(encoding="utf-8"))
    spec["created_ts"] = _time.time() - 30 * 86400
    old_done_path.write_text(json.dumps(spec), encoding="utf-8")

    old_active = lr.new_loop("old active", directory=ldir)
    active_path = ldir / f"{old_active['id']}.json"
    spec = json.loads(active_path.read_text(encoding="utf-8"))
    spec["created_ts"] = _time.time() - 30 * 86400
    active_path.write_text(json.dumps(spec), encoding="utf-8")

    fresh_done = lr.new_loop("fresh done", max_passes=1, directory=ldir)
    lr.run_loop(fresh_done, lambda **kw: "out", directory=ldir)

    removed = lr.prune(max_age_days=7, directory=ldir)

    assert removed == [old_done["id"]]
    assert not old_done_path.exists()
    assert (ldir / f"{old_active['id']}.json").exists()
    assert (ldir / f"{fresh_done['id']}.json").exists()


def test_prune_rejects_negative_age(ldir):
    with pytest.raises(lr.LoopError):
        lr.prune(max_age_days=-1, directory=ldir)
