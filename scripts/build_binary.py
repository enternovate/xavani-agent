#!/usr/bin/env python3
# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""F02: universal binary build script.

Builds a self-contained executable for the current platform using
PyInstaller. The binary bundles the CLI entry point, the core modules,
and the bundled plugins; user config stays in XAVANI_HOME (never
bundled — secrets must not ship inside the binary).

Usage:
    python3 scripts/build_binary.py            # build for this platform
    python3 scripts/build_binary.py --dry-run  # validate config only
    python3 scripts/build_binary.py --name xavani

The --dry-run mode is what CI runs: it validates the build plan
(entry points, module list, output layout) without spending 10 minutes
compiling.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent

# Modules that must be importable at build time (fail fast if missing).
REQUIRED_IMPORTS = [
    "cli",
    "xavani",
    "xavani_bootstrap",
    "xavani_state",
    "xavani_logging",
    "xavani_constants",
]

# Entry points the binary must expose.
ENTRY_POINTS = ["cli:main", "xavani:main"]


def build_plan(name: str = "xavani") -> Dict[str, Any]:
    """The full build plan for the binary."""
    return {
        "name": name,
        "entry_points": ENTRY_POINTS,
        "required_imports": REQUIRED_IMPORTS,
        "pyinstaller": "pyinstaller" in sys.modules or _tool_available("pyinstaller"),
        "output": f"dist/{name}",
    }


def _tool_available(tool: str) -> bool:
    try:
        import importlib.util

        return importlib.util.find_spec(tool) is not None
    except Exception:
        return False


def validate_plan(plan: Dict[str, Any]) -> List[str]:
    """Validate the build plan. Returns a list of problems."""
    problems: List[str] = []
    for module in REQUIRED_IMPORTS:
        try:
            __import__(module)
        except Exception as exc:
            problems.append(f"required import {module} failed: {exc}")
    for entry in ENTRY_POINTS:
        module, _, _attr = entry.partition(":")
        try:
            __import__(module)
        except Exception as exc:
            problems.append(f"entry point {entry} not importable: {exc}")
    if not plan["pyinstaller"]:
        problems.append("pyinstaller not available — run: uv pip install pyinstaller")
    return problems


def dry_run(name: str = "xavani") -> Dict[str, Any]:
    """Validate the build plan without compiling. CI-safe."""
    plan = build_plan(name)
    problems = validate_plan(plan)
    return {"plan": plan, "problems": problems, "ok": not problems}


def main() -> int:
    parser = argparse.ArgumentParser(description="Xavani universal binary build")
    parser.add_argument("--dry-run", action="store_true", help="validate plan only")
    parser.add_argument("--name", default="xavani", help="binary name")
    args = parser.parse_args()

    if args.dry_run:
        result = dry_run(args.name)
        print(json.dumps(result, indent=2))
        return 0 if result["ok"] else 1

    plan = build_plan(args.name)
    problems = validate_plan(plan)
    if problems:
        for problem in problems:
            print(f"ERROR: {problem}", file=sys.stderr)
        return 1

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", args.name,
        "--clean",
        "--noconfirm",
        "cli.py",
    ]
    print("▶ building:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
