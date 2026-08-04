# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""B04: multi-agent consensus measurement.

Measures agreement between independent agent verdicts on the same
question. The consensus engine is deterministic: verdicts are
normalized, clustered by agreement, and reported with the agreement
ratio. High agreement = high confidence; low agreement = surface the
disagreement instead of pretending one answer is right.

Usage::

    from tools.consensus import ConsensusEngine

    engine = ConsensusEngine()
    verdicts = [
        {"agent": "a", "verdict": "yes"},
        {"agent": "b", "verdict": "yes"},
        {"agent": "c", "verdict": "no"},
    ]
    result = engine.measure(verdicts)
    # result["agreement_ratio"] == 2/3
"""

from __future__ import annotations

import collections
import re
from typing import Any, Dict, List, Optional

# Strip filler so "YES." and "yes" cluster together.
_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")


def normalize_verdict(verdict: Any) -> str:
    """Normalize a verdict for comparison."""
    if verdict is None:
        return ""
    return _NORMALIZE_RE.sub(" ", str(verdict).lower()).strip()


def measure_consensus(
    verdicts: List[Dict[str, Any]],
    *,
    min_agents: int = 2,
) -> Dict[str, Any]:
    """Measure consensus across agent verdicts.

    Args:
        verdicts: [{"agent": str, "verdict": any, "confidence": float?}]
        min_agents: Minimum agents needed for a consensus verdict.

    Returns:
        {
          "agents": n,
          "clusters": [{"verdict": str, "count": n, "agents": [...]}],
          "consensus_verdict": str | None,
          "agreement_ratio": float (0..1),
          "disagreement": bool,
        }
    """
    if len(verdicts) < min_agents:
        return {
            "agents": len(verdicts),
            "clusters": [],
            "consensus_verdict": None,
            "agreement_ratio": 0.0,
            "disagreement": False,
        }

    clusters: Dict[str, Dict[str, Any]] = {}
    for entry in verdicts:
        verdict = normalize_verdict(entry.get("verdict"))
        agent = str(entry.get("agent") or "unknown")
        if not verdict:
            continue  # abstention — excluded from the denominator
        cluster = clusters.setdefault(
            verdict, {"verdict": verdict, "count": 0, "agents": []}
        )
        cluster["count"] += 1
        cluster["agents"].append(agent)

    if not clusters:
        return {
            "agents": len(verdicts),
            "clusters": [],
            "consensus_verdict": None,
            "agreement_ratio": 0.0,
            "disagreement": False,
        }

    ordered = sorted(clusters.values(), key=lambda c: (-c["count"], c["verdict"]))
    top = ordered[0]
    # Abstentions do not count against agreement; ratio is over
    # agents that actually delivered a verdict.
    voting_agents = sum(c["count"] for c in ordered)
    agreement_ratio = top["count"] / voting_agents
    consensus = top["verdict"] if agreement_ratio > 0.5 else None

    return {
        "agents": len(verdicts),
        "clusters": ordered,
        "consensus_verdict": consensus,
        "agreement_ratio": round(agreement_ratio, 4),
        "disagreement": len(ordered) > 1 and agreement_ratio <= 0.5,
    }


class ConsensusEngine:
    """Stateless wrapper around :func:`measure_consensus`."""

    def measure(self, verdicts: List[Dict[str, Any]]) -> Dict[str, Any]:
        return measure_consensus(verdicts)
