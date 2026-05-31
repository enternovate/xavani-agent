# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Guidelines Gate Tool — Pre-ship verification.

A tool the agent calls before declaring a task done. It checks the working
diff against the research guidelines principles and returns a structured
verdict (ok/fail/warn) with reasons.

Checks performed:
  * Surgical — diff touches only files relevant to the stated goal.
  * Eval present — a test/eval was added or run for the change.
  * No unearned abstraction — flags new base classes with single callers.
  * Measurement stated — agent provided a concrete before/after signal.
  * Scrub — diff introduces no new prohibited brand references (R1).
  * Stubs intact — diff does not modify skills_hub.py/weixin.py bodies (R2).
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Check implementations
# ---------------------------------------------------------------------------

_SCRUB_PATTERN = re.compile(r"(?i)\b(nous|hermes[-_]?agent)\b")
_STUB_FILES = {"tools/skills_hub.py", "gateway/platforms/weixin.py"}


def _check_surgical(diff_text: str, goal: str) -> Dict[str, Any]:
    """Check that diff touches only files relevant to the stated goal."""
    files_changed = set()
    for line in diff_text.splitlines():
        if line.startswith("diff --git"):
            parts = line.split()
            if len(parts) >= 4:
                # b/path
                fpath = parts[3].lstrip("b/")
                files_changed.add(fpath)

    if len(files_changed) > 20:
        return {
            "check": "surgical",
            "status": "fail",
            "reason": f"Diff touches {len(files_changed)} files — likely too broad for a single goal. "
                      f"Goal: {goal[:100]}",
        }
    if len(files_changed) > 10:
        return {
            "check": "surgical",
            "status": "warn",
            "reason": f"Diff touches {len(files_changed)} files. Verify each is relevant to: {goal[:80]}",
        }
    return {"check": "surgical", "status": "pass", "reason": ""}


def _check_eval_present(diff_text: str) -> Dict[str, Any]:
    """Check that a test or eval was added or modified."""
    test_patterns = re.compile(
        r"(test_|_test\.py|tests/|spec_|_spec\.py|pytest|unittest|assert )", re.IGNORECASE
    )
    if test_patterns.search(diff_text):
        return {"check": "eval_present", "status": "pass", "reason": ""}
    return {
        "check": "eval_present",
        "status": "warn",
        "reason": "No test or eval changes detected in the diff. "
                  "Karpathy: 'eval is all you need' — add a test.",
    }


def _check_no_unearned_abstraction(diff_text: str) -> Dict[str, Any]:
    """Flag new base classes / ABCs / flags with a single caller."""
    abstraction_patterns = [
        (re.compile(r"class\s+\w+.*\b(ABC|Base|Abstract)\b"), "abstract base class"),
        (re.compile(r"@abstractmethod"), "abstract method"),
        (re.compile(r"FEATURE_FLAG|feature_flag"), "feature flag"),
    ]
    hits: List[str] = []
    for pattern, label in abstraction_patterns:
        if pattern.search(diff_text):
            hits.append(label)

    if hits:
        return {
            "check": "no_unearned_abstraction",
            "status": "warn",
            "reason": f"Diff introduces: {', '.join(hits)}. "
                      "Verify each has at least two concrete callers (YAGNI).",
        }
    return {"check": "no_unearned_abstraction", "status": "pass", "reason": ""}


def _check_measurement_stated(goal: str) -> Dict[str, Any]:
    """Check that the agent stated a concrete before/after signal."""
    measurement_hints = [
        "before", "after", "improve", "reduce", "increase",
        "faster", "slower", "win rate", "latency", "throughput",
        "coverage", "pass rate", "error rate", "metric",
        "%", "ms", "seconds", "benchmark",
    ]
    goal_lower = goal.lower()
    if any(hint in goal_lower for hint in measurement_hints):
        return {"check": "measurement_stated", "status": "pass", "reason": ""}

    # "looks good", "seems fine", "should work" are not measurements
    vague_phrases = ["looks good", "seems fine", "should work", "looks reasonable", "seems ok"]
    if any(phrase in goal_lower for phrase in vague_phrases):
        return {
            "check": "measurement_stated",
            "status": "fail",
            "reason": "Goal uses vague language ('looks good'). Provide a concrete before/after signal.",
        }

    return {
        "check": "measurement_stated",
        "status": "warn",
        "reason": "No concrete measurement detected in the goal statement. "
                  "State a before/after signal (e.g. 'latency: 200ms → 150ms').",
    }


def _check_scrub(diff_text: str) -> Dict[str, Any]:
    """Check that diff introduces no new prohibited brand references."""
    for line in diff_text.splitlines():
        # Only check added lines (not removed ones)
        if line.startswith("+") and not line.startswith("+++"):
            if _SCRUB_PATTERN.search(line):
                return {
                    "check": "scrub",
                    "status": "fail",
                    "reason": f"Diff introduces a prohibited reference: {line.strip()[:120]}",
                }
    return {"check": "scrub", "status": "pass", "reason": ""}


def _check_stubs_intact(diff_text: str) -> Dict[str, Any]:
    """Check that diff does not modify the stub file bodies."""
    for line in diff_text.splitlines():
        if line.startswith("diff --git"):
            for stub in _STUB_FILES:
                if stub in line:
                    # Check if the diff actually modifies content (not just whitespace)
                    # We flag any change to the stub files
                    return {
                        "check": "stubs_intact",
                        "status": "fail",
                        "reason": f"Diff modifies stub file {stub}. Stubs must remain unchanged (R2).",
                    }
    return {"check": "stubs_intact", "status": "pass", "reason": ""}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_guidelines_gate(
    diff_text: str,
    goal: str = "",
) -> Dict[str, Any]:
    """Run all gate checks and return a structured verdict.

    Returns:
        {
            "ok": bool,
            "failures": [{"check": str, "reason": str}, ...],
            "warnings": [{"check": str, "reason": str}, ...],
        }
    """
    checks = [
        _check_surgical(diff_text, goal),
        _check_eval_present(diff_text),
        _check_no_unearned_abstraction(diff_text),
        _check_measurement_stated(goal),
        _check_scrub(diff_text),
        _check_stubs_intact(diff_text),
    ]

    failures = [c for c in checks if c["status"] == "fail"]
    warnings = [c for c in checks if c["status"] == "warn"]

    return {
        "ok": len(failures) == 0,
        "failures": [{"check": c["check"], "reason": c["reason"]} for c in failures],
        "warnings": [{"check": c["check"], "reason": c["reason"]} for c in warnings],
    }


def _handle_guidelines_gate(args: Dict[str, Any]) -> str:
    """Tool handler for the guidelines gate."""
    diff_text = args.get("diff_text", "")
    goal = args.get("goal", "")

    if not diff_text:
        return json.dumps({"error": "No diff_text provided."})

    verdict = run_guidelines_gate(diff_text=diff_text, goal=goal)
    return json.dumps(verdict, indent=2)


# ---------------------------------------------------------------------------
# Tool schema
# ---------------------------------------------------------------------------

GUIDELINES_GATE_SCHEMA: Dict[str, Any] = {
    "name": "guidelines_gate",
    "description": (
        "Pre-ship verification gate. Call before declaring a task done. "
        "Pass the working diff (git diff + git diff --cached) and a short "
        "goal statement. Returns a structured verdict (ok/fail/warn) checking: "
        "surgical changes, eval presence, no unearned abstraction, "
        "measurement stated, scrub (no prohibited brand references), stubs intact."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "diff_text": {
                "type": "string",
                "description": "The combined working diff (git diff + git diff --cached output).",
            },
            "goal": {
                "type": "string",
                "description": "A short statement of what the change accomplishes and how to measure success.",
            },
        },
        "required": ["diff_text", "goal"],
    },
}


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

from tools.registry import registry  # noqa: E402

registry.register(
    name="guidelines_gate",
    toolset="skills",
    schema=GUIDELINES_GATE_SCHEMA,
    handler=_handle_guidelines_gate,
    description="Pre-ship verification gate — checks diff against research guidelines.",
    emoji="🔍",
)
