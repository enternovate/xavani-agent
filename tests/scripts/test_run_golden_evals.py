# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for scripts/run_golden_evals.py — eval-gate (harness item 1)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))

from run_golden_evals import (  # noqa: E402
    load_golden_evals,
    resolve_handler,
    run_golden_evals,
)


def _handler_pass(input_text: str) -> str:
    return "hello back"


def _handler_fail(input_text: str) -> str:
    return "wrong answer"


@pytest.fixture()
def evals_path(tmp_path: Path) -> Path:
    path = tmp_path / "golden-evals.json"
    path.write_text(
        json.dumps(
            {
                "name": "golden",
                "cases": [
                    {"id": "greeting", "input": "hello", "expected": "hello back"},
                    {"id": "steer-echo", "input": "steer: remember this", "expected": "steer acknowledged"},
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_load_golden_evals(evals_path: Path) -> None:
    data = load_golden_evals(evals_path)
    assert data["name"] == "golden"
    assert len(data["cases"]) == 2


def test_run_passes_when_handler_matches(evals_path: Path) -> None:
    report = run_golden_evals(evals_path, _handler_pass)
    assert report["passed"] == 1
    assert report["failed"] == 1  # steer-echo expected differs from handler output


def test_run_fails_when_handler_mismatches(evals_path: Path) -> None:
    report = run_golden_evals(evals_path, _handler_fail)
    assert report["failed"] == 2
    assert report["passed"] == 0


def test_missing_golden_file_exits(evals_path: Path, tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="not found"):
        load_golden_evals(tmp_path / "nope.json")


def test_invalid_golden_json_exits(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{nope", encoding="utf-8")
    with pytest.raises(SystemExit, match="JSON invalid"):
        load_golden_evals(bad)


def test_resolve_handler_valid() -> None:
    handler = resolve_handler("tests.agent.test_tool_metrics:_rec")
    assert callable(handler)


def test_resolve_handler_missing_module_exits() -> None:
    with pytest.raises(SystemExit, match="cannot import"):
        resolve_handler("no_such_module_xyz:func")


def test_resolve_handler_missing_func_exits() -> None:
    with pytest.raises(SystemExit, match="not callable"):
        resolve_handler("agent.tool_metrics:no_such_func")
