#!/usr/bin/env python3

# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Regression gate: compare two bench results files.

Fails (exit 1) when median wall time or cost-per-successful-task worsens
by more than the tolerance (default 10%) against the baseline. Usage::

    python3 -m scripts.task_bench.regression_gate baseline.json current.json [--tolerance 0.10]
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Optional


def load_metrics(path: Path) -> Dict[str, Optional[float]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    summary = data.get("summary", data)
    metrics: Dict[str, Optional[float]] = {}
    for key in ("median_wall_s", "cost_per_successful_task_usd", "success_rate"):
        value = summary.get(key)
        metrics[key] = float(value) if value is not None else None
    return metrics


def worsened(baseline: Optional[float], current: Optional[float],
             tolerance: float) -> bool:
    if baseline is None or current is None:
        return False
    if baseline <= 0:
        return False
    return current > baseline * (1.0 + tolerance)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline")
    parser.add_argument("current")
    parser.add_argument("--tolerance", type=float, default=0.10)
    args = parser.parse_args(argv)

    base = load_metrics(Path(args.baseline))
    cur = load_metrics(Path(args.current))

    failures = []
    for key in ("median_wall_s", "cost_per_successful_task_usd"):
        if worsened(base.get(key), cur.get(key), args.tolerance):
            failures.append(
                f"{key}: {base.get(key)} -> {cur.get(key)} "
                f"(tolerance {args.tolerance:.0%} exceeded)"
            )

    print(f"baseline : {base}")
    print(f"current  : {cur}")
    if failures:
        print("REGRESSION GATE FAILED:")
        for line in failures:
            print(f"  - {line}")
        return 1
    print("Regression gate passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
