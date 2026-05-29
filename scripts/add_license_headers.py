#!/usr/bin/env python3
"""Add MIT license header to all .py files that don't already have it."""

import os
import sys

HEADER = """# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""

# Patterns that indicate a file already has the header or a copyright line
HAS_HEADER_PATTERNS = [
    "Copyright (c) 2025-2026 Enternovate",
    "Copyright (c) 2025 Enternovate",
]

# Directories to exclude entirely
EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".venv",
    "venv",
    "env",
    ".egg-info",
    "dist",
    "build",
    ".tox",
    "ui-tui",  # TypeScript/JS
}

# Files to exclude by name
EXCLUDE_FILES = {
    "__init__.py",  # keep short
}

COUNT = 0
SKIPPED = 0


def needs_header(content: str) -> bool:
    """Check if file needs the header."""
    # Skip empty files
    if not content.strip():
        return False

    # Already has our header
    for pat in HAS_HEADER_PATTERNS:
        if pat in content[:500]:
            return False

    # If first line is shebang, check second/third lines for any copyright
    lines = content.splitlines()
    check_lines = lines[:5]

    for line in check_lines:
        if "copyright" in line.lower():
            # Has some copyright notice, skip
            return False

    return True


def add_header(root_dir: str) -> None:
    global COUNT, SKIPPED

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Skip excluded dirs
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]

        for fname in filenames:
            if not fname.endswith(".py"):
                continue
            if fname in EXCLUDE_FILES:
                SKIPPED += 1
                continue

            fpath = os.path.join(dirpath, fname)
            try:
                with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except Exception as e:
                print(f"  [ERR] Could not read {fpath}: {e}", file=sys.stderr)
                continue

            if not needs_header(content):
                SKIPPED += 1
                continue

            # Determine how to insert header
            lines = content.splitlines(keepends=True)

            if lines and lines[0].startswith("#!"):
                # Shebang file: insert after shebang
                new_content = lines[0] + "\n" + HEADER + "".join(lines[1:])
            else:
                new_content = HEADER + content

            try:
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(new_content)
                COUNT += 1
                print(f"  [OK] Added header: {fpath}")
            except Exception as e:
                print(f"  [ERR] Could not write {fpath}: {e}", file=sys.stderr)


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    print(f"Scanning Python files in: {os.path.abspath(root)}")
    print()
    add_header(root)
    print()
    print(f"Done: {COUNT} file(s) updated, {SKIPPED} file(s) skipped (already had headers or excluded).")
