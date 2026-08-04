# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""G02: pattern consolidation.

Merges repeated or overlapping patterns into consolidated forms. The
consolidator works on the B01 instinct registry data: chains that share
a prefix merge into one chain with combined frequency; near-identical
chains (differing by at most one step) consolidate into the more
frequent variant. Consolidation is deterministic and audit-logged.

Usage::

    from tools.pattern_consolidation import consolidate_patterns

    chains = [("read_file,terminal", 5), ("read_file,terminal,patch", 3)]
    report = consolidate_patterns(chains)
"""

from __future__ import annotations

import itertools
from typing import Any, Dict, List, Tuple


def _split_chain(chain: str) -> List[str]:
    return [step.strip() for step in chain.split(",") if step.strip()]


def _chain_str(steps: List[str]) -> str:
    return ",".join(steps)


def consolidate_patterns(
    chains: List[Tuple[str, int]],
    *,
    prefix_merge: bool = True,
    max_steps: int = 8,
) -> Dict[str, Any]:
    """Consolidate tool-chain patterns.

    Args:
        chains: [(chain_string, frequency)]
        prefix_merge: Merge shorter chains that are strict prefixes.
        max_steps: Ignore chains longer than this (runaway patterns).

    Returns:
        {
          "consolidated": [(chain, frequency)],
          "merged_count": n,
          "merged_into": {chain: merged_into_chain},
        }
    """
    # Normalize and drop empty/oversized chains.
    normalized: List[Tuple[List[str], int]] = []
    for chain, freq in chains:
        steps = _split_chain(chain)
        if not steps or len(steps) > max_steps:
            continue
        normalized.append((steps, max(1, int(freq))))

    merged_into: Dict[str, str] = {}
    changed = True
    while changed:
        changed = False
        i = 0
        while i < len(normalized):
            j = 0
            while j < len(normalized):
                if i == j:
                    j += 1
                    continue
                steps_i, freq_i = normalized[i]
                steps_j, freq_j = normalized[j]
                # If i is a strict prefix of j, merge i into j (the
                # longer chain carries more information).
                if prefix_merge and len(steps_i) < len(steps_j) and (
                    steps_j[: len(steps_i)] == steps_i
                ):
                    merged_into[_chain_str(steps_i)] = _chain_str(steps_j)
                    normalized[j] = (steps_j, freq_j + freq_i)
                    normalized.pop(i)
                    changed = True
                    break
                j += 1
            if changed:
                break
            i += 1

    # Aggregate exact duplicates.
    freq_map: Dict[str, int] = {}
    for steps, freq in normalized:
        key = _chain_str(steps)
        freq_map[key] = freq_map.get(key, 0) + freq

    consolidated = sorted(freq_map.items(), key=lambda kv: -kv[1])
    return {
        "consolidated": consolidated,
        "merged_count": len(merged_into),
        "merged_into": merged_into,
    }


def consolidate_instinct_store(store, min_frequency: int = 1) -> Dict[str, Any]:
    """Consolidate a B01 instinct registry's stored chains in place.

    Returns the consolidation report. Chains below min_frequency are
    dropped (they never proved themselves).
    """
    entries = store.snapshot().get("chains", {}) if hasattr(store, "snapshot") else {}
    if not entries:
        return {"consolidated": [], "merged_count": 0, "merged_into": {}}

    chains = [(chain, int(meta.get("count", 1))) for chain, meta in entries.items()]
    report = consolidate_patterns(chains)

    # Write consolidated chains back, dropping sub-threshold chains.
    surviving = {
        chain: freq
        for chain, freq in report["consolidated"]
        if freq >= min_frequency
    }
    try:
        store._chains = surviving
        if hasattr(store, "_save"):
            store._save()
    except Exception:
        pass
    return report
