#!/usr/bin/env python3

# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Nightly channel promotion helper (backlog H190).

Preflight checks before a nightly tag is created:

* the suite summary (JSON with passed/failed counts) shows zero failures,
* CHANGELOG.md has an entry for the current pyproject version,
* no nightly tag already exists for that version.

Dry-run is the default. ``--execute`` creates the annotated tag.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read_version(repo: Path) -> str:
    text = (repo / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"', text, re.MULTILINE)
    if not match:
        raise SystemExit("pyproject.toml has no version field")
    return match.group(1)


def _changelog_has_version(repo: Path, version: str) -> bool:
    changelog = repo / "CHANGELOG.md"
    if not changelog.exists():
        return False
    return f"## [{version}]" in changelog.read_text(encoding="utf-8")


def _latest_nightly_tag(repo: Path) -> str | None:
    proc = subprocess.run(
        ["git", "tag", "--list", "nightly-*"],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        return None
    tags = [t for t in proc.stdout.splitlines() if t.startswith("nightly-")]
    return max(tags) if tags else None


def _summary_green(summary_path: Path) -> bool:
    data = json.loads(summary_path.read_text(encoding="utf-8"))
    failed = int(data.get("failed", 0))
    passed = int(data.get("passed", 0))
    return failed == 0 and passed > 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Nightly channel promotion helper.")
    parser.add_argument(
        "--summary", type=Path, help="suite summary JSON with passed/failed counts"
    )
    parser.add_argument(
        "--execute", action="store_true", help="create the tag (default: dry-run)"
    )
    parser.add_argument("--repo", type=Path, default=None, help="repo root")
    args = parser.parse_args(argv)

    repo = (args.repo or _repo_root()).resolve()
    version = _read_version(repo)

    if args.summary is not None:
        if not args.summary.exists():
            print(f"FAIL: summary file missing: {args.summary}")
            return 1
        if not _summary_green(args.summary):
            print("FAIL: suite summary shows failures; refusing promote")
            return 1

    if not _changelog_has_version(repo, version):
        print(f"FAIL: CHANGELOG.md missing entry for [{version}]")
        return 1

    latest = _latest_nightly_tag(repo)
    if latest is not None and version in latest:
        print(f"FAIL: nightly tag already exists for version {version} ({latest})")
        return 1

    tag = f"nightly-{version}-{datetime.now().strftime('%Y%m%d')}"
    if not args.execute:
        print(f"OK: would create tag {tag}")
        return 0

    proc = subprocess.run(
        ["git", "tag", "-a", tag, "-m", f"nightly {version}"],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        print(f"FAIL: git tag error: {proc.stderr.strip()}")
        return 1
    print(f"OK: created tag {tag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
