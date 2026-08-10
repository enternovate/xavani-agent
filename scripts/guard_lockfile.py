#!/usr/bin/env python3
"""Lockfile commit guard for Xavani Agent.

Blocks commits that stage ``uv.lock`` unless the committer explicitly
opts in by setting ``XAVANI_ALLOW_LOCKFILE_CHANGE=1``.

uv.lock is the dependency ground truth for this repo; CI enforces it via
``.github/workflows/uv-lockfile-check.yml``. Accidental lockfile churn
(platform noise, tool-version drift) pollutes that ground truth, so
normal commits must not carry uv.lock changes.

Exit codes:
    0 -- no staged uv.lock, or change explicitly allowed via env var
    1 -- staged uv.lock without XAVANI_ALLOW_LOCKFILE_CHANGE=1
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ALLOW_ENV = "XAVANI_ALLOW_LOCKFILE_CHANGE"
LOCKFILE = "uv.lock"


def _staged_files(repo_root: Path) -> list[str]:
    """Return the list of staged file paths (git diff --cached --name-only)."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(
            f"guard_lockfile: could not read staged files: {result.stderr.strip()}",
            file=sys.stderr,
        )
        return []
    return [line for line in result.stdout.splitlines() if line]


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    if LOCKFILE not in _staged_files(repo_root):
        return 0

    if os.environ.get(ALLOW_ENV) == "1":
        return 0

    print(
        f"guard_lockfile: {LOCKFILE} is staged but {ALLOW_ENV} is not set.\n"
        f"uv.lock is the dependency ground truth; accidental churn must not "
        f"be committed.\n"
        f"  - If this change is intentional (real dependency update): "
        f"re-run with {ALLOW_ENV}=1.\n"
        f"  - Otherwise: unstage uv.lock and keep the lockfile change out of "
        f"this commit.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
