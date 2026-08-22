#!/usr/bin/env python3

# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Config leaderboard: rank stored bench results by cost per success.

Scans ``scripts/task_bench/results/*.json`` and prints the best configs
first. CLI: ``python3 -m scripts.task_bench.leaderboard [--limit N]``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def load_rankings(results_dir: Path = RESULTS_DIR) -> List[Dict[str, Any]]:
    """Parse every result file into a ranking row; corrupt files skip."""
    rows: List[Dict[str, Any]] = []
    if not results_dir.is_dir():
        return rows
    for path in sorted(results_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        summary = payload.get("summary")
        if not isinstance(summary, dict):
            continue
        cost_per_success = summary.get("cost_per_successful_task_usd")
        rows.append({
            "file": path.name,
            "mode": payload.get("mode"),
            "model": payload.get("model"),
            "provider": payload.get("provider"),
            "task_count": summary.get("task_count"),
            "success_rate": summary.get("success_rate"),
            "median_wall_seconds": summary.get("median_wall_seconds"),
            "cost_per_successful_task_usd": cost_per_success,
        })
    return sorted(rows, key=_rank_key)


def _rank_key(row: Dict[str, Any]) -> tuple:
    cost = row.get("cost_per_successful_task_usd")
    cost_key = float(cost) if isinstance(cost, (int, float)) else float("inf")
    median = row.get("median_wall_seconds")
    median_key = float(median) if isinstance(median, (int, float)) else float("inf")
    return (cost_key, median_key)


def render_rankings(rows: List[Dict[str, Any]]) -> str:
    lines = [
        f"{'rank':<5} {'mode':<6} {'model':<20} {'tasks':>6} "
        f"{'success':>8} {'median_s':>9} {'cost/success':>13}  file"
    ]
    for i, row in enumerate(rows, start=1):
        cost = row.get("cost_per_successful_task_usd")
        cost_str = f"{cost:.6f}" if isinstance(cost, (int, float)) else "n/a"
        rate = row.get("success_rate")
        rate_str = f"{rate * 100:.1f}%" if isinstance(rate, (int, float)) else "n/a"
        median = row.get("median_wall_seconds")
        median_str = f"{median:.4f}" if isinstance(median, (int, float)) else "n/a"
        lines.append(
            f"{i:<5} {str(row.get('mode') or '-'):<6} "
            f"{str(row.get('model') or '-'):<20} "
            f"{row.get('task_count') or 0:>6} {rate_str:>8} "
            f"{median_str:>9} {cost_str:>13}  {row['file']}"
        )
    return "\n".join(lines)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="leaderboard")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--results-dir", default=None)
    args = parser.parse_args(argv)

    results_dir = Path(args.results_dir) if args.results_dir else RESULTS_DIR
    rows = load_rankings(results_dir)[: max(0, args.limit)]
    if not rows:
        print(f"no result files in {results_dir}")
        return 0
    print(render_rankings(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
