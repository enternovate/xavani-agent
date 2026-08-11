#!/usr/bin/env python3

# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Memory recall precision benchmark (backlog E124).

Seeds N distinct facts (each carrying a unique term) into a throwaway
SQLite memory store and measures how precisely ``MemoryManager.search``
recalls them under three query variants:

* exact     — the full unique term; the seeded fact must be the hit,
* partial   — the first 4 characters of the term (a prefix probe),
* unrelated — a term that appears in no seeded fact; must return nothing.

Per query: precision@k = relevant hits / hits returned and recall@k =
1.0 iff the target fact is inside the top-k results, k = the search
limit (default 10). The results table is printed and the process exits
0; pass thresholds live in ``tests/test_memory_benchmark.py``.

The store and the B02 fact extractor's summary file both live under a
fresh temp dir (``XAVANI_HOME`` is repointed there for the duration),
so the real ``~/.xavani`` is never touched. The default backend is the
substring scan; set ``XAVANI_MEMORY_FTS5=1`` to benchmark the FTS5
backend instead — partial-prefix queries then legitimately score 0
because the API is queried without a trailing wildcard.

CLI: ``python3 scripts/memory_benchmark/runner.py [--facts N] [--limit K]``
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from xavani_memory.manager import MemoryManager, _fts5_supported  # noqa: E402

N_FACTS = 20
DEFAULT_LIMIT = 10
_PARTIAL_PREFIX_LEN = 4

_TERMS = [
    "kangaroo", "quokka", "wombat", "platypus", "echidna",
    "bettong", "dunnart", "goanna", "kookaburra", "cockatoo",
    "wallaby", "bandicoot", "numbat", "phascogale", "cassowary",
    "budgerigar", "corella", "currawong", "rosella", "malleefowl",
]

_UNRELATED_TERMS = ["giraffe", "harbour"]


def make_facts(n: int = N_FACTS) -> List[str]:
    """Deterministic distinct fact sentences, one unique term each."""
    if not 1 <= n <= len(_TERMS):
        raise ValueError(f"n must be in [1, {len(_TERMS)}]")
    return [
        f"Fact {i + 1}: the {_TERMS[i]} population survey finished on "
        f"day {i + 1} with {200 + i} sightings."
        for i in range(n)
    ]


def make_queries(n: int = N_FACTS) -> List[Dict[str, str]]:
    """Exact and prefix-partial variants per fact, plus unrelated probes."""
    queries: List[Dict[str, str]] = []
    for term in _TERMS[:n]:
        queries.append({"kind": "exact", "term": term, "query": term})
        queries.append({"kind": "partial", "term": term, "query": term[:_PARTIAL_PREFIX_LEN]})
    for term in _UNRELATED_TERMS:
        queries.append({"kind": "unrelated", "term": "", "query": term})
    return queries


def run_benchmark(
    n_facts: int = N_FACTS,
    limit: int = DEFAULT_LIMIT,
    memory_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Seed ``n_facts`` facts into a fresh store and measure per-query precision."""
    tmp_root: Optional[Path] = None
    if memory_dir is None:
        tmp_root = Path(tempfile.mkdtemp(prefix="memory_benchmark_"))
        memory_dir = tmp_root / "memory"

    prev_home = os.environ.get("XAVANI_HOME")
    os.environ["XAVANI_HOME"] = str(memory_dir.parent)
    manager = MemoryManager(memory_dir=memory_dir, auto_maintenance=False)
    try:
        manager.set_session("memory-benchmark")
        for fact in make_facts(n_facts):
            manager.remember(
                user_input=fact, agent_response="acknowledged", outcome="benchmark"
            )

        rows: List[Dict[str, Any]] = []
        for q in make_queries(n_facts):
            target = q["term"]
            texts = [h[0].get("user_input") or "" for h in manager.search(q["query"], limit=limit)]
            relevant = sum(1 for t in texts if target and target in t)
            rows.append(
                {
                    "kind": q["kind"],
                    "query": q["query"],
                    "target": target or "-",
                    "hits": len(texts),
                    "relevant": relevant,
                    "precision": relevant / len(texts) if texts else 0.0,
                    "recall": 1.0 if relevant else 0.0,
                }
            )

        backend = "fts5" if manager._search_backend == "fts5" and _fts5_supported() else "substring"
        return {
            "facts_total": n_facts,
            "limit": limit,
            "backend": backend,
            "memory_dir": str(memory_dir),
            "queries": rows,
        }
    finally:
        try:
            manager.stop_maintenance()
        except Exception:
            pass
        if prev_home is None:
            os.environ.pop("XAVANI_HOME", None)
        else:
            os.environ["XAVANI_HOME"] = prev_home
        if tmp_root is not None:
            shutil.rmtree(tmp_root, ignore_errors=True)


def _aggregate(rows: List[Dict[str, Any]], kind: Optional[str] = None) -> Dict[str, Any]:
    subset = [r for r in rows if kind is None or r["kind"] == kind]
    hits = sum(r["hits"] for r in subset)
    relevant = sum(r["relevant"] for r in subset)
    return {
        "queries": len(subset),
        "hits": hits,
        "relevant": relevant,
        "precision": relevant / hits if hits else 0.0,
        "recall": sum(r["recall"] for r in subset) / len(subset) if subset else 0.0,
    }


def _print_report(result: Dict[str, Any]) -> None:
    rows = result["queries"]
    print("memory recall precision benchmark (backlog E124)")
    print(
        f"store: {result['memory_dir']}   backend: {result['backend']}   "
        f"facts: {result['facts_total']}   k (limit): {result['limit']}   "
        f"queries: {len(rows)}"
    )
    print()
    print(f"{'kind':<10} {'query':<14} {'target':<14} {'hits':>4} {'relevant':>8} {'precision@k':>11} {'recall@k':>9}")
    for r in rows:
        print(
            f"{r['kind']:<10} {r['query']:<14} {r['target']:<14} {r['hits']:>4} "
            f"{r['relevant']:>8} {r['precision']:>11.3f} {r['recall']:>9.3f}"
        )
    print()
    print("aggregate by variant")
    print(f"{'kind':<10} {'queries':>7} {'hits':>5} {'relevant':>8} {'precision@k':>11} {'recall@k':>9}")
    for kind in ("exact", "partial", "unrelated"):
        agg = _aggregate(rows, kind)
        print(
            f"{kind:<10} {agg['queries']:>7} {agg['hits']:>5} {agg['relevant']:>8} "
            f"{agg['precision']:>11.3f} {agg['recall']:>9.3f}"
        )
    overall = _aggregate(rows)
    print(
        f"{'overall':<10} {overall['queries']:>7} {overall['hits']:>5} {overall['relevant']:>8} "
        f"{overall['precision']:>11.3f} {overall['recall']:>9.3f}"
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="memory_benchmark",
        description="Memory recall precision benchmark against MemoryManager.search.",
    )
    parser.add_argument("--facts", type=int, default=N_FACTS, help=f"facts to seed (max {len(_TERMS)})")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="search limit k")
    parser.add_argument("--memory-dir", type=Path, default=None, help="reuse an existing memory dir")
    args = parser.parse_args(argv)

    if not 1 <= args.facts <= len(_TERMS):
        parser.error(f"--facts must be between 1 and {len(_TERMS)}")
    if args.limit < 1:
        parser.error("--limit must be >= 1")

    _print_report(run_benchmark(n_facts=args.facts, limit=args.limit, memory_dir=args.memory_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
