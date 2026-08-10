#!/usr/bin/env python3
"""Performance baseline measurement for the xavani-agent repo.

Emits ONE JSON object on stdout (nothing else — diagnostics go to stderr):

    {
      "startup_seconds":     median wall time of `python3 -c "import cli"` in fresh subprocesses,
                             or null (with "startup_error") if every repeat failed or timed out,
      "system_prompt_tokens": estimated tokens of the default identity system prompt,
      "tool_schema_tokens":   estimated tokens of the full JSON tool-schema list,
      "tools_sent":           number of tool definitions sent to the model
    }

Token estimate = ceil(chars / 4) (a standard heuristic; documented in each
measurement below).

Usage:
    python3 scripts/perf_baseline.py [--quick]

    --quick  run a single startup repeat instead of 3 (median).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Allow importing from repo root on a bare checkout (mirrors
# scripts/tool_payload_report.py).
sys.path.insert(0, str(REPO_ROOT))

# Some model_tools imports expect XAVANI_HOME to exist.
os.environ.setdefault("XAVANI_HOME", os.path.join(os.path.expanduser("~"), ".xavani"))


def est_tokens(text: str) -> int:
    """Rough token estimate: ceil(chars / 4)."""
    return math.ceil(len(text) / 4)


def collect_startup_samples(repeats: int) -> tuple[list[float], list[str]]:
    """Wall times of a cold `python3 -c "import cli"` in fresh subprocesses.

    Each repeat is a brand-new interpreter process so module-level imports
    (cli.py is ~15k lines, ~3.7s cold) are counted every time. Repeats that
    fail (nonzero exit) or time out are skipped; returns (sorted valid
    samples, error descriptions).
    """
    samples: list[float] = []
    errors: list[str] = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        try:
            proc = subprocess.run(
                [sys.executable, "-c", "import cli"],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            errors.append("timed out after 60s")
            print("warning: `import cli` repeat timed out after 60s", file=sys.stderr)
            continue
        dt = time.perf_counter() - t0
        if proc.returncode != 0:
            err = f"rc={proc.returncode}: {proc.stderr.strip()[:300]}"
            errors.append(err)
            print(f"warning: `import cli` repeat failed ({err})", file=sys.stderr)
            continue
        samples.append(dt)
    samples.sort()
    return samples, errors


def measure_system_prompt_tokens() -> int:
    """Estimated tokens of the default identity system prompt.

    Static path: agent/system_prompt.build_system_prompt() requires a live
    AIAgent instance (memory store, tool names, model/provider, etc.), which
    cannot be constructed cheaply here. The persistent identity the agent
    actually reads is the seeded SOUL.md template, DEFAULT_SOUL_MD from
    xavani_cli/default_soul.py — it is computed at import time and includes
    the mandatory research-guidelines splice (non-removable by design), so it
    is a faithful static proxy for the "stable" system-prompt tier.
    """
    from xavani_cli.default_soul import DEFAULT_SOUL_MD

    return est_tokens(DEFAULT_SOUL_MD)


def measure_tool_schema() -> tuple[int, int]:
    """(tool_schema_tokens, tools_sent) for the full tool definitions list.

    Mirrors the agent's real model call: get_tool_definitions(enabled_toolsets=None,
    quiet_mode=True) returns every toolset's OpenAI-format schemas; the prompt
    payload is the json.dumps of that list.
    """
    import model_tools

    defs = model_tools.get_tool_definitions(enabled_toolsets=None, quiet_mode=True)
    schema_json = json.dumps(defs)
    return est_tokens(schema_json), len(defs)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--quick",
        action="store_true",
        help="run a single startup repeat instead of 3 (median)",
    )
    args = parser.parse_args()

    repeats = 1 if args.quick else 3
    samples, startup_errors = collect_startup_samples(repeats)
    system_prompt_tokens = measure_system_prompt_tokens()
    tool_schema_tokens, tools_sent = measure_tool_schema()

    # Median of valid samples (1 repeat -> the single sample). If every
    # repeat failed/timed out, report null + startup_error and still exit 0:
    # this is a measurement tool, not a gate.
    startup_seconds = (
        round(samples[len(samples) // 2], 4) if samples else None
    )

    baseline = {
        "startup_seconds": startup_seconds,
        "system_prompt_tokens": system_prompt_tokens,
        "tool_schema_tokens": tool_schema_tokens,
        "tools_sent": tools_sent,
    }
    if not samples:
        baseline["startup_error"] = (
            "; ".join(startup_errors) or "all startup repeats failed or timed out"
        )
    print(json.dumps(baseline, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
