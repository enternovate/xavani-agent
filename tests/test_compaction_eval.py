# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Compaction quality eval harness tests (backlog E120).

Verifies the harness contract against the REAL
``ContextCompressor.compress`` path with a scripted (LLM-free)
summarizer:

* a faithful summary retains >= 80% of the seeded facts,
* a degraded summary scores strictly lower (guards the scorer),
* the CLI runner prints a score table and exits 0.

Mirrors the faux-provider pattern (tests/harness/faux_provider.py): the
LLM call is scripted at a transport seam; everything else is production
code.
"""

import subprocess
import sys
from pathlib import Path

from scripts.compaction_eval.runner import (
    RETENTION_PASS,
    make_facts,
    normalize,
    run_eval,
    score_retention,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_faithful_summary_retains_at_least_80_percent_of_facts():
    result = run_eval()

    assert result["facts_total"] >= 20
    assert result["faithful_retention"] >= RETENTION_PASS


def test_degraded_summary_scores_strictly_lower_than_faithful():
    result = run_eval()

    assert result["degraded_retention"] < result["faithful_retention"]
    assert result["degraded_retention"] < RETENTION_PASS


def test_runner_cli_prints_score_table_and_exits_zero():
    runner = _REPO_ROOT / "scripts" / "compaction_eval" / "runner.py"
    proc = subprocess.run(
        [sys.executable, str(runner)],
        capture_output=True,
        text=True,
        cwd=_REPO_ROOT,
        timeout=120,
    )

    assert proc.returncode == 0, proc.stderr
    assert "retention" in proc.stdout.lower()


def test_normalization_collapses_case_and_whitespace():
    assert normalize("  Alpha   BETA\n") == "alpha beta"


def test_scorer_matches_facts_across_case_and_whitespace_variants():
    facts = make_facts(2)
    summary = facts[0].upper().replace(" ", "  \n ")
    retained, total = score_retention(summary, facts)

    assert retained == 1
    assert total == 2
