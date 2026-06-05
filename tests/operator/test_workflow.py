# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the durable workflow/DAG engine (v0.7.0 operator U79/U80/U84)."""

from __future__ import annotations

import pytest

from xavani_operator.state import OperatorState
from xavani_operator.workflow import Workflow, WorkflowStep


def _step(sid, fn, deps=None, key=""):
    return WorkflowStep(id=sid, run=fn, deps=deps or [], idempotency_key=key)


def test_runs_steps_in_dependency_order():
    order = []
    wf = Workflow([
        _step("c", lambda c: order.append("c"), deps=["b"]),
        _step("a", lambda c: order.append("a")),
        _step("b", lambda c: order.append("b"), deps=["a"]),
    ])
    wf.run()
    assert order == ["a", "b", "c"]


def test_failed_step_blocks_dependents():
    ran = []

    def boom(ctx):
        raise RuntimeError("x")

    res = Workflow([
        _step("a", boom),
        _step("b", lambda c: ran.append("b"), deps=["a"]),
    ]).run(max_retries=0)
    assert res["a"]["status"] == "failed"
    assert res["b"]["status"] == "blocked"
    assert "b" not in ran


def test_retries_then_succeeds():
    counter = {"n": 0}

    def flaky(ctx):
        counter["n"] += 1
        if counter["n"] < 2:
            raise RuntimeError("transient")
        return "ok"

    res = Workflow([_step("a", flaky)]).run(max_retries=2)
    assert res["a"]["status"] == "done"
    assert counter["n"] == 2


def test_idempotent_resume_skips_done(tmp_path):
    st = OperatorState(root=tmp_path)
    ran = []
    steps = [
        _step("a", lambda c: ran.append("a")),
        _step("b", lambda c: ran.append("b"), deps=["a"]),
    ]
    Workflow(steps, store=st, name="wf1").run()
    assert ran == ["a", "b"]

    ran.clear()
    res = Workflow(steps, store=st, name="wf1").run()  # resume — all done
    assert ran == []
    assert res["a"]["status"] == "skipped"


def test_partial_resume_completes(tmp_path):
    st = OperatorState(root=tmp_path)
    ran = []

    def boom(ctx):
        raise RuntimeError("crash after a")

    # First run: a succeeds, b crashes.
    Workflow([_step("a", lambda c: ran.append("a")), _step("b", boom)], store=st, name="wf2").run(max_retries=0)
    assert ran == ["a"]

    # Second run with a fixed b: a is skipped (done), b now runs.
    ran.clear()
    res = Workflow(
        [_step("a", lambda c: ran.append("a")), _step("b", lambda c: ran.append("b"))],
        store=st, name="wf2",
    ).run()
    assert ran == ["b"]
    assert res["a"]["status"] == "skipped"
    assert res["b"]["status"] == "done"


def test_cycle_is_detected():
    wf = Workflow([
        _step("a", lambda c: None, deps=["b"]),
        _step("b", lambda c: None, deps=["a"]),
    ])
    with pytest.raises(ValueError):
        wf.run()
