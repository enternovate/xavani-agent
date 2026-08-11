#!/usr/bin/env python3

# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Compaction quality eval harness (backlog E120).

Seeds N distinct facts into a synthetic session, runs the REAL
``ContextCompressor.compress`` path (window selection, pruning,
serialization, prompt construction, redaction, summary merge, prefix),
then scores how many seeded fact phrases survive in the compacted
summary using normalized LLM-free substring matching.

The summarizer LLM call is scripted at the ``agent.context_compressor.
call_llm`` seam — the compression analogue of the faux-provider pattern
(tests/harness/faux_provider.py patches ``run_agent.OpenAI``): the fake
summarizer is a deterministic function of the prompt the real pipeline
built, so the eval measures pipeline fidelity, not model capability.

Two scripted summarizers guard each other:

* faithful  — reproduces every seeded fact it can find in the prompt,
  so retention measures whether the real compaction path delivered the
  facts into the summarizer input (threshold: ``RETENTION_PASS``).
* degraded  — reproduces a quarter of them, so a broken scorer that
  always returns high (or low) numbers is caught by the strict
  inequality between the two scores.

CLI: ``python3 scripts/compaction_eval/runner.py`` prints a score table
and exits 0.  The pass thresholds are enforced by
``tests/test_compaction_eval.py``, not by the exit code.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional, Tuple
from unittest.mock import patch

# Make ``agent.*`` importable when run as a script from anywhere.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from agent.context_compressor import SUMMARY_PREFIX, ContextCompressor  # noqa: E402

N_FACTS = 25
RETENTION_PASS = 0.80
_DEGRADED_KEEP_FRACTION = 0.25

_CITIES = [
    "Lisbon", "Oslo", "Prague", "Riga", "Sofia", "Turin", "Utrecht",
    "Vienna", "Zurich", "Lyon", "Bilbao", "Cork", "Dresden", "Eindhoven",
    "Florence", "Ghent", "Hamburg", "Innsbruck", "Jyvaskyla", "Krakow",
    "Leipzig", "Malmö", "Nancy", "Ostrava", "Porto",
]

_STRIP_PUNCT = ".,;:!?()[]{}\"'`"


def normalize(text: str) -> str:
    """Lowercase, collapse whitespace, strip edge punctuation."""
    collapsed = " ".join(text.lower().split())
    return collapsed.strip(_STRIP_PUNCT)


def make_facts(n: int = N_FACTS) -> List[str]:
    """Deterministic distinct fact sentences, one per seeded item.

    Every fact carries unique values (q-id, crate count, item id, city,
    day) so no fact is a substring of another and the scorer cannot
    false-positive across facts.
    """
    return [
        f"Shipment q-{1000 + i} carried {220 + i} crates of item "
        f"{i * 7 + 3:04d} and docked at {_CITIES[i % len(_CITIES)]} on day {i + 1}."
        for i in range(n)
    ]


def build_session_messages(facts: List[str]) -> List[Dict[str, Any]]:
    """Synthetic session: system prompt + one exchange per fact + wrap-up."""
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": "You are Xavani, a helpful agent."},
    ]
    for fact in facts:
        messages.append({"role": "user", "content": fact})
        messages.append({"role": "assistant", "content": f"Acknowledged: {fact}"})
    messages.append({"role": "user", "content": "Wrap up the session now."})
    return messages


def facts_seen_in_prompt(prompt: str, facts: List[str]) -> List[str]:
    """Facts the scripted summarizer can find in the real pipeline prompt."""
    haystack = normalize(prompt)
    return [fact for fact in facts if normalize(fact) in haystack]


def _faithful_summarizer(prompt: str, facts: List[str]) -> str:
    seen = facts_seen_in_prompt(prompt, facts)
    actions = "\n".join(f"- {fact}" for fact in seen)
    return f"## Completed Actions\n{actions}\n\n## Remaining Work\nNone."


def _degraded_summarizer(prompt: str, facts: List[str]) -> str:
    seen = facts_seen_in_prompt(prompt, facts)
    keep = seen[: max(1, int(len(seen) * _DEGRADED_KEEP_FRACTION))]
    actions = "\n".join(f"- {fact}" for fact in keep)
    return f"## Completed Actions\n{actions}\n\n## Remaining Work\nNone."


def extract_summary_text(messages: List[Dict[str, Any]]) -> str:
    """Concatenate the compaction handoff summary from compressed messages."""
    parts = []
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, str) and content.lstrip().startswith(SUMMARY_PREFIX):
            parts.append(content)
    if not parts:
        return ""
    text = parts[0].split(SUMMARY_PREFIX, 1)[1]
    # Standalone user-role summaries carry a trailing end marker; drop it.
    return re.split(r"\n--- END OF CONTEXT SUMMARY", text)[0]


def score_retention(summary_text: str, facts: List[str]) -> Tuple[int, int]:
    """(retained, total) — normalized substring match per seeded fact."""
    haystack = normalize(summary_text)
    retained = sum(1 for fact in facts if normalize(fact) in haystack)
    return retained, len(facts)


def run_compaction(
    facts: List[str],
    summarizer: Callable[[str, List[str]], str],
) -> Dict[str, Any]:
    """Run the real compress() path with a scripted summarizer LLM call."""
    messages = build_session_messages(facts)
    seen: List[str] = []
    prompt_text = ""

    def _scripted_call_llm(**kwargs: Any) -> Any:
        nonlocal prompt_text
        prompt_text = kwargs["messages"][0]["content"]
        summary = summarizer(prompt_text, facts)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=summary))]
        )

    compressor = ContextCompressor(model="faux-model", quiet_mode=True)
    with patch("agent.context_compressor.call_llm", new=_scripted_call_llm):
        compressed = compressor.compress(messages)

    seen = facts_seen_in_prompt(prompt_text, facts)
    return {
        "messages": compressed,
        "prompt": prompt_text,
        "seen": len(seen),
        "summary": extract_summary_text(compressed),
    }


def run_eval(n_facts: int = N_FACTS) -> Dict[str, Any]:
    """Score both scripted summarizers against the same seeded session."""
    facts = make_facts(n_facts)
    faithful = run_compaction(facts, _faithful_summarizer)
    degraded = run_compaction(facts, _degraded_summarizer)

    faithful_retained, total = score_retention(faithful["summary"], facts)
    degraded_retained, _ = score_retention(degraded["summary"], facts)
    return {
        "facts_total": total,
        "faithful_seen": faithful["seen"],
        "faithful_retained": faithful_retained,
        "faithful_retention": faithful_retained / total if total else 0.0,
        "degraded_seen": degraded["seen"],
        "degraded_retained": degraded_retained,
        "degraded_retention": degraded_retained / total if total else 0.0,
    }


def _pct(fraction: float) -> str:
    return f"{fraction * 100:.1f}%"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compaction quality eval harness (backlog E120)."
    )
    parser.add_argument(
        "--facts",
        type=int,
        default=N_FACTS,
        help=f"number of seeded facts (default: {N_FACTS})",
    )
    args = parser.parse_args(argv)
    if args.facts < 1:
        parser.error("--facts must be at least 1")

    result = run_eval(args.facts)
    total = result["facts_total"]
    print("compaction quality eval (E120)")
    print(f"  facts seeded:          {total}")
    print(
        f"  faithful summary:      {result['faithful_retained']}/{total} "
        f"facts retained ({_pct(result['faithful_retention'])} retention, "
        f"{result['faithful_seen']}/{total} reached summarizer)"
    )
    print(
        f"  degraded summary:      {result['degraded_retained']}/{total} "
        f"facts retained ({_pct(result['degraded_retention'])} retention, "
        f"{result['degraded_seen']}/{total} reached summarizer)"
    )
    passed = (
        result["faithful_retention"] >= RETENTION_PASS
        and result["degraded_retention"] < result["faithful_retention"]
    )
    print(
        f"  verdict:               {'PASS' if passed else 'FAIL'} "
        f"(faithful >= {RETENTION_PASS:.0%}, degraded < faithful)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
