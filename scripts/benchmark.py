#!/usr/bin/env python3
# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""E10: performance regression detector.

Measures p95 latency of critical Xavani code paths and compares against
a stored baseline. Fails (exit 1) when any p95 regresses more than the
threshold (default 20%), so CI catches performance regressions instead
of letting them accumulate invisibly.

Usage:
    python3 scripts/benchmark.py                      # run + compare
    python3 scripts/benchmark.py --update-baseline    # store new baseline
    python3 scripts/benchmark.py --threshold 0.25     # 25% tolerance

Baseline file: scripts/benchmark-baseline.json (committed).
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Callable, Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent
BASELINE_FILE = Path(__file__).resolve().parent / "benchmark-baseline.json"
DEFAULT_THRESHOLD = 0.20  # 20% regression tolerance
SAMPLES = 7


def _p95(values: List[float]) -> float:
    """Interpolated 95th percentile."""
    if not values:
        return 0.0
    sorted_v = sorted(values)
    if len(sorted_v) == 1:
        return sorted_v[0]
    idx = 0.95 * (len(sorted_v) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(sorted_v) - 1)
    frac = idx - lo
    return sorted_v[lo] + frac * (sorted_v[hi] - sorted_v[lo])


def _time_subprocess_import(module: str) -> float:
    """Measure cold import time in a fresh interpreter (ms)."""
    import subprocess
    import sys

    code = f"import time; t=time.perf_counter(); import {module}; print((time.perf_counter()-t)*1000)"
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=60,
    )
    try:
        return float(result.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return 0.0


def run_benchmarks() -> Dict[str, float]:
    """Run every benchmark, returning name -> p95 ms.

    Each benchmark imports a core module in a FRESH interpreter, so the
    measurement captures the real cold-import cost (module cache in the
    current process would otherwise hide it).
    """
    benchmarks: Dict[str, str] = {
        "import_tools": "tools",
        "import_registry": "tools.registry",
        "config_load": "xavani_cli.config",
        "state_schema": "xavani_state",
    }
    results: Dict[str, float] = {}
    for name, module in benchmarks.items():
        samples = []
        for _ in range(SAMPLES):
            samples.append(_time_subprocess_import(module))
        results[name] = round(_p95(samples), 3)
    return results


def load_baseline() -> Dict[str, float]:
    """Load the committed baseline, or {} when missing."""
    if not BASELINE_FILE.exists():
        return {}
    try:
        return json.loads(BASELINE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def store_baseline(results: Dict[str, float]) -> None:
    """Persist a new baseline file."""
    BASELINE_FILE.write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def compare(results: Dict[str, float], baseline: Dict[str, float],
            threshold: float) -> List[str]:
    """Return a list of regression messages (empty = pass)."""
    problems: List[str] = []
    for name, p95 in sorted(results.items()):
        base = baseline.get(name)
        if base is None or base <= 0:
            continue  # new benchmark or empty baseline — nothing to compare
        change = (p95 - base) / base
        if change > threshold:
            problems.append(
                f"{name}: p95 {p95:.1f}ms vs baseline {base:.1f}ms "
                f"(+{change * 100:.0f}% > +{threshold * 100:.0f}% threshold)"
            )
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update-baseline", action="store_true",
                        help="Store the current run as the new baseline")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                        help="Regression tolerance (default 0.20)")
    parser.add_argument("--json", action="store_true",
                        help="Emit machine-readable JSON")
    args = parser.parse_args()

    results = run_benchmarks()

    if args.update_baseline:
        store_baseline(results)
        print(f"Baseline updated: {json.dumps(results)}")
        return 0

    baseline = load_baseline()
    problems = compare(results, baseline, args.threshold)

    if args.json:
        print(json.dumps({
            "results": results,
            "problems": problems,
            "passed": not problems,
        }))
    else:
        for name, p95 in sorted(results.items()):
            base = baseline.get(name)
            suffix = f" (baseline {base:.1f}ms)" if base else " (no baseline)"
            print(f"  {name:<20} {p95:>8.1f} ms{suffix}")
        if problems:
            print("\nPERFORMANCE REGRESSIONS DETECTED:")
            for msg in problems:
                print(f"  ✗ {msg}")
            return 1
        if baseline:
            print("\n✓ All benchmarks within threshold")
        else:
            print("\n(no baseline — run with --update-baseline to store one)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
