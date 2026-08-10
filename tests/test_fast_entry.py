# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""S2-7: fast --version/--help entry path (backlog A21).

The console entry point must answer --version/--help without importing the
heavy ``cli`` module (~1.06s warm import). These tests run the real entry
point as a subprocess; the elapsed-time bound on --version fails loudly if
the fast path regresses back to the full import.
"""

import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Mirrors xavani_main's version branch in xavani.py — kept in sync with
# the VERSION/PRODUCT_NAME/PRONUNCIATION/VENDOR constants there.
EXPECTED_VERSION_OUTPUT = (
    "Xavani Agent v0.1.1\n"
    "Pronounced: shahr-vaa-nee\n"
    "Built by Enternovate — Open Source\n"
    "MIT License — Free for any use.\n"
)


def _run_xavani(*args: str) -> tuple[subprocess.CompletedProcess, float]:
    start = time.monotonic()
    proc = subprocess.run(
        [sys.executable, "-m", "xavani", *args],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=10,
    )
    return proc, time.monotonic() - start


def test_version_exits_zero_quickly_and_prints_version():
    proc, elapsed = _run_xavani("--version")
    assert proc.returncode == 0
    assert elapsed < 1.0
    assert proc.stdout == EXPECTED_VERSION_OUTPUT


def test_help_exits_zero():
    proc, _ = _run_xavani("--help")
    assert proc.returncode == 0
    assert "Usage: xavani" in proc.stdout


def test_unknown_flag_falls_through_to_cli():
    proc, _ = _run_xavani("--bogus-flag")
    assert proc.returncode != 0
    assert "Could not consume arg: --bogus-flag" in proc.stderr
