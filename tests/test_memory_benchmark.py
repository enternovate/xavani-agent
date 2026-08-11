# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Memory recall precision benchmark harness tests (backlog E124).

Verifies the harness contract against the REAL ``MemoryManager.search``
path on a throwaway SQLite store:

* an exact-term query retrieves the seeded fact (precision 1.0),
* an unrelated query returns no hits (precision 0.0),
* the CLI runner prints a results table and exits 0.

Deterministic under either search backend: the assertions hold for the
default substring scan and for FTS5. The store and the B02 fact
extractor's summary file live in a temp dir (the runner repoints
``XAVANI_HOME`` there), so the real ``~/.xavani`` is never touched.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.memory_benchmark.runner import N_FACTS, make_facts, run_benchmark

_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_make_facts_are_distinct_and_deterministic():
    facts = make_facts(N_FACTS)

    assert len(facts) == N_FACTS
    assert len(set(facts)) == N_FACTS
    assert make_facts(N_FACTS) == facts


def test_exact_term_query_returns_the_seeded_fact():
    result = run_benchmark(n_facts=N_FACTS)

    exact = [q for q in result["queries"] if q["kind"] == "exact"]
    assert len(exact) == N_FACTS
    assert all(q["recall"] == 1.0 for q in exact)
    assert all(q["precision"] == 1.0 for q in exact)


def test_unrelated_query_returns_no_hits():
    result = run_benchmark(n_facts=N_FACTS)

    unrelated = [q for q in result["queries"] if q["kind"] == "unrelated"]
    assert unrelated
    assert all(q["hits"] == 0 for q in unrelated)
    assert all(q["precision"] == 0.0 for q in unrelated)


def test_partial_queries_report_bounded_precision():
    result = run_benchmark(n_facts=N_FACTS)

    partial = [q for q in result["queries"] if q["kind"] == "partial"]
    assert len(partial) == N_FACTS
    assert all(0.0 <= q["precision"] <= 1.0 for q in partial)


def test_runner_cli_prints_table_and_exits_zero():
    runner = _REPO_ROOT / "scripts" / "memory_benchmark" / "runner.py"
    proc = subprocess.run(
        [sys.executable, str(runner)],
        capture_output=True,
        text=True,
        cwd=_REPO_ROOT,
        timeout=120,
    )

    assert proc.returncode == 0, proc.stderr
    assert "precision" in proc.stdout.lower()
    assert "exact" in proc.stdout.lower()
