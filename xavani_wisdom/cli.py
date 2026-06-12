# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""CLI dispatch for ``xavani wisdom`` — the Oracle from the terminal (v1.0.0 ②).

Two subcommands:
  verdict <text...>   project a plan's consequences + flag downfall patterns
  corpus              list the ascent/downfall wisdom corpus

Thin layer; deterministic, zero-LLM (R10). Wired into ``xavani_cli/main.py``.
"""

from __future__ import annotations

from typing import Any


def cmd_wisdom(args: Any) -> None:
    """Dispatch a ``xavani wisdom <subcommand>`` invocation."""
    command = getattr(args, "wisdom_command", None)
    if command == "corpus":
        _corpus()
    elif command == "verdict":
        _verdict(args)
    else:
        print("Usage:")
        print("  xavani wisdom verdict <describe a plan or decision>")
        print("  xavani wisdom corpus")


def _verdict(args: Any) -> None:
    from xavani_wisdom.consequence import project

    parts = getattr(args, "text", None) or []
    text = " ".join(parts).strip() if isinstance(parts, list) else str(parts).strip()
    if not text:
        print("Tell me what to weigh, e.g.  xavani wisdom verdict take on debt to expand fast")
        return

    r = project({"text": text})
    print(f"⚖  Oracle verdict — {text}\n")
    print(
        f"   risk={r.risk:.2f}   expected value={r.expected_value:.2f}   "
        f"reversibility={r.reversibility:.2f}   tail risk={r.tail_risk:.2f}"
    )
    if r.base_rate_flag:
        print("   ⚠ base-rate denial detected (\"this time is different\")")
    if r.downfall_signals:
        print(f"   downfall signals: {', '.join(r.downfall_signals)}")
    for finding in r.findings:
        print(f"   • {finding}")
    if not r.downfall_signals and not r.findings:
        print("   No known downfall pattern detected — proceed with normal care.")


def _corpus() -> None:
    from xavani_wisdom.patterns import load_corpus

    corpus = load_corpus()
    ascent = [p for p in corpus if p.kind == "ascent"]
    downfall = [p for p in corpus if p.kind == "downfall"]
    print(
        f"Xavani Oracle corpus — {len(corpus)} patterns "
        f"({len(ascent)} ascent, {len(downfall)} downfall)\n"
    )
    for p in sorted(corpus, key=lambda x: (x.kind, x.id)):
        mark = "↗ rose " if p.kind == "ascent" else "↘ fell "
        print(f"  {mark} {p.figure}")
        print(f"      {p.the_lesson}")
