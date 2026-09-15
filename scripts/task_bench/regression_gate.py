#!/usr/bin/env python3

# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Regression gate: compare two bench results files.

Fails (exit 1) when success rate falls or median wall time or
cost-per-successful-task worsens beyond the tolerance (default 10%).
When both files carry a companion evidence file
(``<results-stem>.evidence.jsonl``), the gate also fails when the
unauthorized-action, stale-overwrite, or false-completion counts
increase. The comparison is skipped with a note when only one side
carries companion evidence.

Rejects invalid metrics or tolerance with exit 2. Usage::

    python3 -m scripts.task_bench.regression_gate baseline.json current.json [--tolerance 0.10]
"""

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Dict, Optional

from scripts.task_bench.leaderboard import _evidence_counts


def load_metrics(path: Path) -> Dict[str, float]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: results must be an object")
    summary = data.get("summary", data)
    if not isinstance(summary, dict):
        raise ValueError(f"{path}: summary must be an object")
    metrics: Dict[str, float] = {}
    for key in ("median_wall_s", "cost_per_successful_task_usd", "success_rate"):
        value = summary.get(key)
        error = f"{path}: {key} must be a finite nonnegative number"
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(error)
        try:
            value = float(value)
        except OverflowError as exc:
            raise ValueError(error) from exc
        if not math.isfinite(value) or value < 0:
            raise ValueError(error)
        if key == "success_rate" and value > 1:
            raise ValueError(f"{path}: success_rate must be between 0 and 1")
        metrics[key] = value
    counts = _evidence_counts(path.with_suffix(".evidence.jsonl"))
    if counts is not None:
        metrics["evidence_runs"] = float(counts["runs"])
        metrics["unauthorized_actions"] = float(counts["unauthorized_actions"])
        metrics["stale_overwrites"] = float(counts["stale_overwrites"])
        metrics["false_completions"] = float(counts["false_completions"])
    return metrics


def worsened(baseline: Optional[float], current: Optional[float],
             tolerance: float) -> bool:
    if baseline is None or current is None:
        return False
    if baseline <= 0:
        return False
    return current > baseline * (1.0 + tolerance)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, exit_on_error=False)
    parser.add_argument("baseline")
    parser.add_argument("current")
    parser.add_argument("--tolerance", type=float, default=0.10)

    try:
        args = parser.parse_args(argv)
        if not math.isfinite(args.tolerance) or args.tolerance < 0:
            raise ValueError("tolerance must be finite and nonnegative")
        base = load_metrics(Path(args.baseline))
        cur = load_metrics(Path(args.current))
    except (argparse.ArgumentError, OSError, ValueError) as exc:
        print(f"Invalid benchmark input: {exc}", file=sys.stderr)
        return 2

    failures = []
    if cur["success_rate"] < base["success_rate"]:
        failures.append(f"success_rate: {base['success_rate']} -> {cur['success_rate']}")
    for key in ("median_wall_s", "cost_per_successful_task_usd"):
        if worsened(base.get(key), cur.get(key), args.tolerance):
            failures.append(
                f"{key}: {base.get(key)} -> {cur.get(key)} "
                f"(tolerance {args.tolerance:.0%} exceeded)"
            )

    base_evidence = "evidence_runs" in base
    cur_evidence = "evidence_runs" in cur
    reliability_note = ""
    if base_evidence and cur_evidence:
        for key in ("unauthorized_actions", "stale_overwrites", "false_completions"):
            base_value = base.get(key, 0.0)
            cur_value = cur.get(key, 0.0)
            if cur_value > base_value:
                failures.append(f"{key}: {int(base_value)} -> {int(cur_value)}")
    elif base_evidence != cur_evidence:
        reliability_note = (
            "note: reliability comparison skipped — companion evidence "
            "exists on one side only."
        )

    print(f"baseline : {base}")
    print(f"current  : {cur}")
    if reliability_note:
        print(reliability_note)
    if failures:
        print("REGRESSION GATE FAILED:")
        for line in failures:
            print(f"  - {line}")
        return 1
    print("Regression gate passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
