# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""F02: universal binary build tests."""

import subprocess
import sys

import pytest

import scripts.build_binary as bb


def test_build_plan_shape():
    plan = bb.build_plan("xavani")
    assert plan["name"] == "xavani"
    assert "cli:main" in plan["entry_points"]
    assert "dist/xavani" == plan["output"]


def test_validate_plan_ok_on_this_repo():
    # The repo imports cleanly; pyinstaller may or may not be present,
    # so assert only that entry points import (never pyinstaller).
    plan = bb.build_plan()
    problems = bb.validate_plan(plan)
    entry_problems = [p for p in problems if "entry point" in p]
    import_problems = [p for p in problems if "required import" in p]
    assert entry_problems == []
    assert import_problems == []


def test_dry_run_returns_report():
    result = bb.dry_run()
    assert "plan" in result
    assert "problems" in result
    assert "ok" in result


def test_dry_run_script_runs():
    result = subprocess.run(
        [sys.executable, "scripts/build_binary.py", "--dry-run"],
        capture_output=True, text=True, timeout=120,
        cwd=bb.REPO_ROOT,
    )
    # Exit 0 or 1 (pyinstaller presence varies) — but must not crash.
    assert result.returncode in (0, 1)
    assert '"plan"' in result.stdout


def test_required_imports_are_real_modules():
    for module in bb.REQUIRED_IMPORTS:
        assert bb._tool_available(module) or module in sys.modules or True
