#!/usr/bin/env python3
# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""C18: automatic env var documentation generator.

Scans the codebase for ``os.environ`` reads and ``os.getenv`` calls and
emits a documented reference of every env var: name, purpose (inferred
from the call site comment when available), default, and first-seen
location.

Usage:
    python3 scripts/generate_env_docs.py [--output docs/reference/env-vars.md]

The scanner is conservative: it collects variable names from the
patterns Xavani actually uses, and it never executes code. Comments on
the line above a call site are captured as the purpose hint.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Paths that are not part of the runtime surface.
SKIP_DIRS = {".git", ".venv", "node_modules", "website", "web", "ui-tui",
             "dist", "build", "landingpage", "__pycache__"}
SKIP_FILES = {"generate_env_docs.py"}

# os.getenv("NAME", default) — literal first arg.
_GETENV_RE = re.compile(r"""os\.getenv\(\s*["']([A-Za-z_][A-Za-z0-9_]*)["']""")
# os.environ["NAME"] read.
_ENVIRON_GET_RE = re.compile(r"""os\.environ\.get\(?\s*["']([A-Za-z_][A-Za-z0-9_]*)["']""")
# os.environ["NAME"] = ... writes are collected too (config surface).
_ENVIRON_SET_RE = re.compile(r"""os\.environ\[["']([A-Za-z_][A-Za-z0-9_]*)["']\]\s*=""")
# ContextVar-backed env fallbacks: get_session_env("NAME", ...) and
# get_env_value("NAME", ...) — same env surface as os.getenv.
_SESSION_ENV_RE = re.compile(r"""(?:get_session_env|get_env_value)\(\s*["']([A-Za-z_][A-Za-z0-9_]*)["']""")
# getenv-style helper with env-var name first arg.
_ENV_HELPER_RE = re.compile(r"""os\.environ\.get\("([A-Za-z_][A-Za-z0-9_]*)"\)""")


def _iter_py_files(root: Path):
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if path.name in SKIP_FILES:
            continue
        yield path


def _purpose_hint(lines: list[str], idx: int) -> str:
    """Capture the nearest preceding comment as the purpose hint."""
    for j in range(idx - 1, max(idx - 4, -1), -1):
        line = lines[j].strip()
        if line.startswith("#"):
            hint = line.lstrip("#").strip()
            if hint:
                return hint
        elif line and not line.startswith((" ", "\t")):
            # A new statement starts — stop scanning upward.
            return ""
    return ""


def scan_codebase(root: Path) -> dict[str, dict]:
    """Return {VAR_NAME: {defaults, locations, hints}}."""
    found: dict[str, dict] = defaultdict(
        lambda: {"defaults": set(), "locations": [], "hints": []}
    )
    for path in _iter_py_files(root):
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for idx, line in enumerate(lines):
            patterns = (_GETENV_RE, _ENVIRON_GET_RE, _ENVIRON_SET_RE,
                        _SESSION_ENV_RE, _ENV_HELPER_RE)
            for pat in patterns:
                for m in pat.finditer(line):
                    name = m.group(1)
                    entry = found[name]
                    default = None
                    if pat is _GETENV_RE:
                        dm = re.search(r""",\s*["']([^"']*)["']\s*\)""", line[m.end():])
                        if dm:
                            default = dm.group(1)
                    loc = f"{path.relative_to(root)}:{idx + 1}"
                    if loc not in entry["locations"]:
                        entry["locations"].append(loc)
                    if default and default not in entry["defaults"]:
                        entry["defaults"].add(default)
                    hint = _purpose_hint(lines, idx)
                    if hint and hint not in entry["hints"]:
                        entry["hints"].append(hint)
    return found


def render_markdown(found: dict[str, dict]) -> str:
    """Render the env-var reference as markdown."""
    out = [
        "# Environment Variables Reference",
        "",
        "This file is AUTO-GENERATED. Do not edit by hand.",
        "Regenerate with: `python3 scripts/generate_env_docs.py`",
        "",
        f"Scanned: {len(found)} environment variables.",
        "",
    ]
    for name in sorted(found):
        entry = found[name]
        out.append(f"## `{name}`")
        out.append("")
        if entry["hints"]:
            out.append("**Purpose:** " + entry["hints"][0])
            out.append("")
        if entry["defaults"]:
            out.append("**Defaults:** " + ", ".join(sorted(entry["defaults"])))
            out.append("")
        out.append("**Used at:**")
        for loc in entry["locations"][:8]:
            out.append(f"- `{loc}`")
        if len(entry["locations"]) > 8:
            out.append(f"- ... and {len(entry['locations']) - 8} more")
        out.append("")
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", "-o", default=str(REPO_ROOT / "docs" / "reference" / "env-vars.md"),
        help="Output markdown path (default: docs/reference/env-vars.md)",
    )
    parser.add_argument(
        "--count", action="store_true", help="Only print the env var count",
    )
    args = parser.parse_args()

    found = scan_codebase(REPO_ROOT)
    if args.count:
        print(len(found))
        return 0

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_markdown(found), encoding="utf-8")
    print(f"Wrote {len(found)} env vars to {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
