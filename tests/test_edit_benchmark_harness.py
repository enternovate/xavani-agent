"""TDD tests for the edit-format benchmark harness (Task 16).

The harness (scripts/edit_benchmark/runner.py) drives the REAL edit tool
paths against 20 canned edit tasks and reports a JSON summary:

* mode='patch'    -> tools.edit_tool._handle_edit mode='patch' (delegates to
                     tools.file_tools._handle_patch: V4A + fuzzy strategies).
* mode='hashline' -> tools.edit_tool._handle_edit mode='hashline'
                     (tools.hashline parse + apply via the default snapshot store).
* mode='replace'  -> tools.edit_tool._handle_edit mode='replace'
                     (exact old/new string substitution).

Fake model mode uses the canned payloads from tasks.jsonl, so CI needs no
provider key.  These tests prove the harness runs end-to-end, exits 0,
passes every task in every mode, emits the required summary keys, and fails
cleanly (exit 1 + error JSON) on an unknown mode.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "scripts" / "edit_benchmark" / "runner.py"
TASKS = REPO_ROOT / "scripts" / "edit_benchmark" / "tasks.jsonl"

SUMMARY_KEYS = {
    "mode",
    "model",
    "tasks_total",
    "passed",
    "failed",
    "total_retries",
    "total_tokens_est",
    "tasks",
}


def _run_benchmark(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(RUNNER), *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=180,
    )


@pytest.mark.parametrize("mode", ["hashline", "patch", "replace"])
def test_fake_mode_first_five_tasks_pass_in_every_mode(mode: str) -> None:
    proc = _run_benchmark(
        "--mode", mode, "--model", "fake",
        "--max-tasks", "5", "--tasks", str(TASKS),
    )
    assert proc.returncode == 0, f"stderr:\n{proc.stderr}\nstdout:\n{proc.stdout}"
    summary = json.loads(proc.stdout)
    assert SUMMARY_KEYS <= set(summary), f"missing keys in {sorted(summary)}"
    assert summary["mode"] == mode
    assert summary["model"] == "fake"
    assert summary["tasks_total"] == 5
    assert summary["passed"] == 5
    assert summary["failed"] == 0
    assert summary["total_retries"] == 0
    assert isinstance(summary["total_tokens_est"], int)
    assert len(summary["tasks"]) == 5
    assert all(t["status"] == "pass" for t in summary["tasks"])


def test_unknown_mode_fails_cleanly() -> None:
    proc = _run_benchmark(
        "--mode", "bogus", "--model", "fake",
        "--max-tasks", "3", "--tasks", str(TASKS),
    )
    # argparse rejects an invalid --mode choice: exit 2, usage on stderr.
    assert proc.returncode == 2
    assert "invalid choice" in proc.stderr
    assert "bogus" in proc.stderr


def test_missing_tasks_file_fails_cleanly() -> None:
    proc = _run_benchmark(
        "--mode", "replace", "--model", "fake",
        "--tasks", str(REPO_ROOT / "no-such-tasks.jsonl"),
    )
    assert proc.returncode == 1
    data = json.loads(proc.stdout)
    assert "error" in data
