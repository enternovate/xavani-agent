# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""A04: deterministic xdist ordering — loadscope + pinned env.

The canonical runner and CI must group module tests on one worker
(--dist=loadscope) and pin the runtime (TZ, PYTHONHASHSEED) so local
runs match CI. These guard tests fail loudly if the flags drift.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def test_runner_pins_loadscope():
    runner = _read(REPO_ROOT / "scripts" / "run_tests.sh")
    assert "--dist=loadscope" in runner, (
        "run_tests.sh must pass --dist=loadscope to pytest (A04)"
    )


def test_runner_pins_worker_count():
    runner = _read(REPO_ROOT / "scripts" / "run_tests.sh")
    assert 'WORKERS="${XAVANI_TEST_WORKERS:-4}"' in runner


def test_runner_pins_deterministic_env():
    runner = _read(REPO_ROOT / "scripts" / "run_tests.sh")
    assert "export PYTHONHASHSEED=0" in runner
    assert "export TZ=UTC" in runner


def test_ci_core_job_uses_loadscope():
    workflow = _read(REPO_ROOT / ".github" / "workflows" / "tests.yml")
    assert "--dist=loadscope" in workflow
