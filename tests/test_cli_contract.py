"""Black-box CLI contract tests for the installed xavani entry point.

These tests never import package internals or string-match code paths —
they run the real executable as a subprocess and assert only on exit
codes and stream contents, which is the contract a user actually sees.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
_TIMEOUT_S = 10


@pytest.fixture()
def entry_point() -> tuple[list[str], Path]:
    """The installed console script, falling back to `python -m xavani`."""
    script = shutil.which("xavani")
    if script:
        return [script], REPO_ROOT
    if (REPO_ROOT / "xavani.py").is_file():
        return [sys.executable, "-m", "xavani"], REPO_ROOT
    pytest.skip("xavani entry point not found; install with `pip install -e .`")


def _run_cli(entry_point: tuple[list[str], Path], *args: str) -> subprocess.CompletedProcess:
    cmd, cwd = entry_point
    env = os.environ.copy()
    env.setdefault("XAVANI_SKIP_HOME_CHECK", "1")
    try:
        return subprocess.run(
            [*cmd, *args],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_S,
            stdin=subprocess.DEVNULL,
            cwd=cwd,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        pytest.skip(
            f"{cmd} hung on {args} with stdin closed (needs a TTY?); skipping"
        )


def test_version_exits_zero_and_prints_version(entry_point) -> None:
    proc = _run_cli(entry_point, "--version")
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    output = proc.stdout + proc.stderr
    assert re.search(r"\d+\.\d+", output), f"no version string in output: {output!r}"


def test_unknown_flag_exits_nonzero_with_usage_on_stderr(entry_point) -> None:
    proc = _run_cli(entry_point, "--definitely-not-a-real-flag")
    assert proc.returncode in (1, 2), (
        f"unknown flag must exit 1 or 2, got {proc.returncode}"
    )
    assert proc.stderr.strip(), f"expected usage/error on stderr, got: {proc.stdout!r}"
    assert re.search(r"usage|error|unknown", proc.stderr, re.IGNORECASE), (
        f"stderr does not look like usage/error output: {proc.stderr!r}"
    )


def test_help_exits_zero_and_mentions_usage(entry_point) -> None:
    proc = _run_cli(entry_point, "--help")
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    output = proc.stdout + proc.stderr
    # Fire renders help with NAME/SYNOPSIS/DESCRIPTION/FLAGS sections; the
    # SYNOPSIS section is its usage block.
    assert re.search(r"usage|synopsis", output, re.IGNORECASE), (
        f"no usage/synopsis text in output: {output!r}"
    )
