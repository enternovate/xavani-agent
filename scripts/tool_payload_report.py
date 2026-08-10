#!/usr/bin/env python3
"""Tool schema payload token report.

Measures the per-turn tool schema token cost — per tool and per toolset —
for the exact OpenAI-style definitions sent to the model API. This is the
evidence generator for deferred-tool decisions.

Usage:
    python3 scripts/tool_payload_report.py            # JSON on stdout
    python3 scripts/tool_payload_report.py --human    # + top-10 table on stderr

Stdout carries JSON ONLY. Logs, warnings, and the human-readable summary
go to stderr.
"""

import json
import math
import os
import sys
from collections import defaultdict

# Allow importing from repo root (mirrors scripts/build_skills_index.py)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

# Some model_tools imports expect XAVANI_HOME to exist.
os.environ.setdefault("XAVANI_HOME", os.path.join(os.path.expanduser("~"), ".xavani"))

import model_tools  # noqa: E402


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token (chars/4 heuristic)."""
    return math.ceil(len(text) / 4)


def build_report():
    """Compute the per-tool / per-toolset token payload report."""
    definitions = model_tools.get_tool_definitions(
        enabled_toolsets=None, quiet_mode=True
    )

    tools = []
    by_toolset = defaultdict(lambda: {"tools": 0, "tokens": 0})
    total_tokens = 0

    for tool in definitions:
        function = tool.get("function", {}) if isinstance(tool, dict) else {}
        name = function.get("name") or tool.get("name", "<unnamed>")
        # Whole tool entry is the payload sent to the API.
        tokens = estimate_tokens(json.dumps(tool))
        toolset = model_tools.get_toolset_for_tool(name) or "unknown"
        tools.append({"name": name, "toolset": toolset, "tokens": tokens})
        by_toolset[toolset]["tools"] += 1
        by_toolset[toolset]["tokens"] += tokens
        total_tokens += tokens

    return {
        "token_estimate": "chars/4",
        "total_tools": len(tools),
        "total_tokens": total_tokens,
        "tools": tools,
        "by_toolset": dict(by_toolset),
    }


def print_human_summary(report):
    """Top-10 tools by token cost, printed to stderr."""
    top = sorted(report["tools"], key=lambda t: t["tokens"], reverse=True)[:10]
    print(f"\nTool schema payload token report (estimate: {report['token_estimate']})",
          file=sys.stderr)
    print(f"Total tools: {report['total_tools']}  Total tokens: {report['total_tokens']}",
          file=sys.stderr)
    print(f"{'#':>3}  {'tokens':>6}  {'toolset':<22}  name", file=sys.stderr)
    print("-" * 60, file=sys.stderr)
    for i, t in enumerate(top, 1):
        print(f"{i:>3}  {t['tokens']:>6}  {t['toolset']:<22}  {t['name']}",
              file=sys.stderr)


def main() -> int:
    report = build_report()
    print(json.dumps(report))
    if "--human" in sys.argv[1:]:
        print_human_summary(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
