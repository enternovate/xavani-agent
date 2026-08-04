# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""C04: latency comparison report.

Compares provider/model latency from the E01 metrics collector and
answers "which model is actually fastest for my workload?" with
numbers. The report is a snapshot: median and p95 latency per model,
call counts, and a ranked "fastest first" ordering.

Usage::

    from xavani_observability.latency_report import build_latency_report

    report = build_latency_report(collector)
    print(report["ranking"])   # fastest model first
"""

from __future__ import annotations

from typing import Any, Dict, List

# Models with fewer than this many recorded calls are excluded from the
# ranking (a single lucky call is not evidence).
MIN_CALLS_FOR_RANKING = 3


def _median(values: List[float]) -> float:
    if not values:
        return 0.0
    sorted_v = sorted(values)
    n = len(sorted_v)
    if n % 2 == 1:
        return sorted_v[n // 2]
    return (sorted_v[n // 2 - 1] + sorted_v[n // 2]) / 2.0


def _p95(values: List[float]) -> float:
    if not values:
        return 0.0
    sorted_v = sorted(values)
    idx = min(len(sorted_v) - 1, int(len(sorted_v) * 0.95))
    return sorted_v[idx]


def build_latency_report(collector) -> Dict[str, Any]:
    """Build the latency comparison report from a metrics collector.

    Reads the collector's per-model LLM latency series. Returns:

    - ``models``: per-model stats (calls, median_ms, p95_ms, min_ms, max_ms)
    - ``ranking``: model names, fastest median first (min 3 calls)
    - ``generated_at``: epoch seconds
    """
    latencies: Dict[str, List[float]] = {}
    try:
        with collector._lock:
            for model, series in collector._llm_latencies.items():
                latencies[model] = list(series)
    except Exception:
        # Fall back to the public accessor shape if internals change.
        try:
            latencies = dict(getattr(collector, "_llm_latencies", {}))
        except Exception:
            latencies = {}

    models: Dict[str, Dict[str, Any]] = {}
    for model, series in latencies.items():
        if not series:
            continue
        models[model] = {
            "calls": len(series),
            "median_ms": round(_median(series), 1),
            "p95_ms": round(_p95(series), 1),
            "min_ms": round(min(series), 1),
            "max_ms": round(max(series), 1),
        }

    ranking = sorted(
        (m for m, s in models.items() if s["calls"] >= MIN_CALLS_FOR_RANKING),
        key=lambda m: models[m]["median_ms"],
    )

    return {
        "models": models,
        "ranking": ranking,
        "generated_at": __import__("time").time(),
    }


def format_latency_report(report: Dict[str, Any]) -> str:
    """Render the report as a compact console block."""
    lines = ["Latency comparison (per model, ms):"]
    if not report["models"]:
        lines.append("  no latency data recorded yet")
        return "\n".join(lines)
    lines.append(
        "  {:<24} {:>6} {:>8} {:>8} {:>8}".format(
            "model", "calls", "median", "p95", "max"
        )
    )
    ordered = sorted(
        report["models"].items(),
        key=lambda kv: (kv[1]["median_ms"], kv[1]["calls"]),
    )
    for model, stats in ordered:
        lines.append(
            "  {:<24} {:>6} {:>8} {:>8} {:>8}".format(
                model[:24],
                stats["calls"],
                stats["median_ms"],
                stats["p95_ms"],
                stats["max_ms"],
            )
        )
    if report["ranking"]:
        fastest = report["ranking"][0]
        lines.append(f"  fastest (median): {fastest}")
    return "\n".join(lines)
