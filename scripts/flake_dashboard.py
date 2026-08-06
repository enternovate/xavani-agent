#!/usr/bin/env python3
# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.


"""E06: flake dashboard — parse tests/flakiness.json into a report.

Reads the JSON array produced by the flake-capture harness, groups the
failures by test id, and renders a markdown report with the top flaky
tests and root-cause labels so CI can surface it as an artifact page.

Usage:
    python3 scripts/flake_dashboard.py --json tests/flakiness.json --out /tmp/flakes.md
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


def load_entries(path: str) -> List[Dict[str, Any]]:
    """Load the flakiness JSON array (or {"entries": [...]} wrapper)."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = data.get("entries", [])
    return [e for e in data if isinstance(e, dict)]


def build_report(entries: List[Dict[str, Any]], top: int = 10) -> str:
    """Render the markdown flake dashboard report."""
    per_test: Dict[str, List[Dict[str, Any]]] = {}
    label_counter: Counter = Counter()
    category_counter: Counter = Counter()
    for entry in entries:
        test_id = str(entry.get("test_id") or "unknown")
        per_test.setdefault(test_id, []).append(entry)
        label = str(entry.get("label") or "").strip()
        if label:
            label_counter[label] += 1
        category_counter[str(entry.get("category") or "unknown")] += 1

    ranked = sorted(per_test.items(), key=lambda kv: -len(kv[1]))
    lines = ["# Flake Dashboard", ""]
    lines.append(
        f"Total recorded failures: **{len(entries)}** across "
        f"**{len(per_test)}** test(s)."
    )
    lines.append("")
    lines.append("## Top flaky tests")
    lines.append("")
    lines.append("| Test | Failures | Root-cause label |")
    lines.append("|------|----------|------------------|")
    for test_id, rows in ranked[:top]:
        label = str(rows[0].get("label") or "").strip()
        lines.append(f"| `{test_id}` | {len(rows)} | {label} |")
    lines.append("")
    lines.append("## Root-cause label counts")
    lines.append("")
    for label, count in label_counter.most_common():
        lines.append(f"- {label}: {count}")
    lines.append("")
    lines.append("## Failure categories")
    lines.append("")
    for cat, count in category_counter.most_common():
        lines.append(f"- {cat}: {count}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the flake dashboard report (E06).")
    parser.add_argument("--json", required=True, help="path to tests/flakiness.json")
    parser.add_argument("--out", required=True, help="output markdown path")
    parser.add_argument("--top", type=int, default=10, help="top-N flaky tests to list")
    args = parser.parse_args()

    try:
        entries = load_entries(args.json)
    except OSError as exc:
        print(f"flake_dashboard: cannot read {args.json}: {exc}", file=sys.stderr)
        return 1

    report = build_report(entries, top=args.top)
    Path(args.out).write_text(report, encoding="utf-8")
    distinct = len({str(e.get("test_id")) for e in entries})
    print(f"✓ wrote {args.out} ({len(entries)} failures across {distinct} tests)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
