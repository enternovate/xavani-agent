#!/usr/bin/env python3
# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""A06: forked race detector.

Thread-pool races (MOA, approval, cron) are invisible to threaded xdist
workers because all threads share the GIL and module state. Running the
same tests in FORKED subprocesses exposes races: each fork gets a fresh
interpreter, so module-level state contamination between tests can no
longer be masked by in-process reuse.

This script runs the race-prone modules under ``pytest-forked`` and
reports failures. CI runs it as a complement to the normal suite.

Usage:
    python3 scripts/run_forked_race_tests.py            # default modules
    python3 scripts/run_forked_race_tests.py --all      # every test module
    python3 scripts/run_forked_race_tests.py tests/tools/test_approval.py
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Race-prone modules: heavy module-level state, threads, or shared caches.
RACE_PRONE_MODULES = [
    "tests/tools/test_approval.py",
    "tests/tools/test_mixture_of_agents_tool.py",
    "tests/gateway/test_approve_deny_commands.py",
    "tests/tools/test_tirith_security.py",
    "tests/tools/test_write_approval.py",
    "tests/cron/",
    "tests/xavani_state/",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="Test paths (default: race-prone set)")
    parser.add_argument("--all", action="store_true",
                        help="Run every test module under --forked")
    parser.add_argument("--workers", type=int, default=4,
                        help="xdist workers (default 4)")
    args = parser.parse_args()

    if args.all:
        targets = ["tests/"]
    elif args.paths:
        targets = args.paths
    else:
        targets = RACE_PRONE_MODULES

    cmd = [
        sys.executable, "-m", "pytest",
        "-o", "addopts=",
        "-n", str(args.workers),
        "--dist=loadscope",
        "--forked",
        "--ignore=tests/integration",
        "--ignore=tests/e2e",
        "-m", "not integration",
        "-q",
        "--tb=line",
        *targets,
    ]
    print("▶ forked race run:", " ".join(str(t) for t in targets))
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    if result.returncode != 0:
        print("\nFORKED RACE FAILURES DETECTED — see failures above.")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
