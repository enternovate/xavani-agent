# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""CLI for the research guidelines enforcement — ``xavani guidelines …`` subcommand.

Exposes three subcommands:

  * ``list``  — print the full roster in priority order.
  * ``show <name>`` — print the full body of a guideline.
  * ``check`` — run the guidelines gate against the current diff.

Mirrors the subcommand pattern from ``xavani_cli/kanban.py``.
"""

from __future__ import annotations

import argparse
import shlex
import sys
from typing import Optional


# ---------------------------------------------------------------------------
# Argparse surface
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser for ``xavani guidelines …``."""
    parser = argparse.ArgumentParser(
        prog="xavani guidelines",
        description="Research guidelines enforcement commands.",
    )
    sub = parser.add_subparsers(dest="guidelines_action")

    sub.add_parser("list", help="List all mandatory guidelines in priority order")

    show_p = sub.add_parser("show", help="Show the full body of a guideline")
    show_p.add_argument("name", help="Guideline name (e.g. karpathy-guidelines)")

    sub.add_parser("check", help="Run the guidelines gate against the current diff")

    return parser


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


def _cmd_list() -> int:
    """Print the full roster."""
    from xavani_cli.research_guidelines import list_guideline_names, get_guideline

    names = list_guideline_names()
    if not names:
        print("No mandatory guidelines found.")
        return 1

    print(f"Mandatory Research Guidelines ({len(names)} total):\n")
    print(f"  {'Name':<30s} {'Domain':<25s} {'Priority':>8s}")
    print(f"  {'─' * 30} {'─' * 25} {'─' * 8}")
    for name in names:
        g = get_guideline(name)
        if g:
            print(f"  {g.name:<30s} {g.domain:<25s} {g.priority:>8d}")
    return 0


def _cmd_show(name: str) -> int:
    """Print the full body of a guideline."""
    from xavani_cli.research_guidelines import get_guideline

    if not name:
        print("Usage: xavani guidelines show <name>")
        return 1

    g = get_guideline(name)
    if g is None:
        print(f"Guideline not found: {name}")
        print("Use 'xavani guidelines list' to see available guidelines.")
        return 1

    print(f"# {g.name}")
    print(f"Domain: {g.domain} | Priority: {g.priority} | Version: {g.version}")
    print(f"Description: {g.description}")
    if g.sources:
        print(f"Sources: {', '.join(g.sources)}")
    print(f"\n{'─' * 60}\n")
    print(g.body)
    return 0


def _cmd_check() -> int:
    """Run the guidelines gate against the current diff."""
    import json
    import subprocess

    # Collect the working diff
    diff_result = subprocess.run(
        ["git", "diff", "--no-color"],
        capture_output=True, text=True, timeout=30,
    )
    cached_result = subprocess.run(
        ["git", "diff", "--cached", "--no-color"],
        capture_output=True, text=True, timeout=30,
    )
    diff_text = (diff_result.stdout or "") + (cached_result.stdout or "")

    if not diff_text.strip():
        print("No uncommitted changes found. Nothing to check.")
        return 0

    # Run the gate tool
    from tools.guidelines_gate_tool import run_guidelines_gate

    verdict = run_guidelines_gate(
        diff_text=diff_text,
        goal="CLI-initiated guidelines check",
    )

    # Format output
    if verdict.get("ok"):
        print("✓ Guidelines gate: PASSED")
    else:
        print("✗ Guidelines gate: FAILED")

    if verdict.get("failures"):
        print("\nFailures:")
        for f in verdict["failures"]:
            print(f"  ✗ [{f['check']}] {f['reason']}")

    if verdict.get("warnings"):
        print("\nWarnings:")
        for w in verdict["warnings"]:
            print(f"  ⚠ [{w['check']}] {w['reason']}")

    if verdict.get("ok") and not verdict.get("warnings"):
        print("\nAll checks passed. No warnings.")

    return 0 if verdict.get("ok") else 1


# ---------------------------------------------------------------------------
# Command dispatch
# ---------------------------------------------------------------------------


def guidelines_command(args: argparse.Namespace) -> int:
    """Entry point from ``xavani guidelines …`` argparse dispatch.

    Returns a shell-style exit code (0 on success, non-zero on error).
    """
    action = getattr(args, "guidelines_action", None)

    if action == "list":
        return _cmd_list()
    elif action == "show":
        return _cmd_show(getattr(args, "name", ""))
    elif action == "check":
        return _cmd_check()
    else:
        build_parser().print_help()
        return 0


def run_slash(rest: str) -> str:
    """Execute a ``/guidelines …`` string and return captured stdout/stderr.

    ``rest`` is everything after ``/guidelines`` (may be empty). Used from
    both the interactive CLI and the gateway so formatting is identical.
    """
    import io
    import contextlib

    tokens = shlex.split(rest) if rest and rest.strip() else []

    parser = build_parser()
    buf_out = io.StringIO()
    buf_err = io.StringIO()

    if not tokens:
        tokens = ["list"]

    try:
        args = parser.parse_args(tokens)
    except SystemExit as exc:
        if exc.code == 0:
            # --help was requested
            return buf_out.getvalue() or buf_err.getvalue() or ""
        return f"⚠ /guidelines usage error\n{buf_err.getvalue()}"
    except argparse.ArgumentError as exc:
        return f"⚠ /guidelines usage error\n{exc}"

    with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
        try:
            guidelines_command(args)
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)

    output = buf_out.getvalue()
    errors = buf_err.getvalue()
    if errors:
        output = f"{output}\n{errors}" if output else errors
    return output.strip()
