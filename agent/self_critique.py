# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Self-critique pass (harness item 3, HARNESS_UPGRADES_0115.md).

Config-gated final-answer review: the model reviews its own answer against
a rubric (correctness, completeness, citations, STE compliance) and may
rewrite it once. The loop is bounded to 1 iteration — never infinite.

Pure module: rubric parsing, threshold logic, and the bounded-loop driver
are all testable without a live model (inject a reviewer callable).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

# Rubric keys the reviewer prompt must cover. Order = display order.
RUBRIC_KEYS = ("correctness", "completeness", "citations", "ste_compliance")

DEFAULT_RUBRIC = {
    "correctness": "Is the answer factually correct? Flag errors.",
    "completeness": "Does the answer cover the whole question? Flag gaps.",
    "citations": "Are claims grounded in cited sources where required?",
    "ste_compliance": "Is the prose short, active-voice, and free of AI-isms?",
}

MAX_FIX_ITERATIONS = 1


class RubricError(ValueError):
    """Raised when a rubric is malformed."""


def parse_rubric(raw: Any) -> Dict[str, str]:
    """Validate a rubric mapping (key -> criterion)."""
    if not isinstance(raw, dict):
        raise RubricError("rubric must be a mapping of criterion -> description")
    cleaned: Dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not key.strip():
            raise RubricError(f"invalid rubric key: {key!r}")
        if not isinstance(value, str) or not value.strip():
            raise RubricError(f"rubric criterion for {key!r} must be non-empty text")
        cleaned[key.strip()] = value.strip()
    if not cleaned:
        raise RubricError("rubric must contain at least one criterion")
    return cleaned


def build_review_prompt(answer: str, rubric: Dict[str, str]) -> str:
    """Compose the self-review prompt for one answer."""
    criteria = "\n".join(f"- {key}: {criterion}" for key, criterion in rubric.items())
    return (
        "Review the answer below against each criterion.\n"
        "Answer the question: does it need one fix pass?\n"
        "If it does, output the fixed answer after a line containing only 'FIX:'.\n"
        "If it is already good, output 'OK'.\n\n"
        f"Critería:\n{criteria}\n\nAnswer:\n{answer}"
    )


def extract_fix(review: str) -> Optional[str]:
    """Extract the rewritten answer after a 'FIX:' marker, if present."""
    marker = re.search(r"^FIX:\s*$", review, flags=re.MULTILINE)
    if marker is None:
        return None
    rest = review[marker.end():].strip()
    return rest or None


def run_self_critique(
    answer: str,
    reviewer: Callable[[str], str],
    rubric: Optional[Dict[str, str]] = None,
    enabled: bool = True,
    max_iterations: int = MAX_FIX_ITERATIONS,
) -> Dict[str, Any]:
    """Run the bounded self-critique pass.

    ``reviewer`` maps a prompt to the model's review text. Returns the
    final answer, whether a fix was applied, and the iteration count.
    """
    if not enabled:
        return {"answer": answer, "fixed": False, "iterations": 0}
    rubric = parse_rubric(rubric if rubric is not None else DEFAULT_RUBRIC)

    current = answer
    iterations = 0
    fixed = False
    for _ in range(max_iterations):
        prompt = build_review_prompt(current, rubric)
        review = reviewer(prompt)
        replacement = extract_fix(review)
        if replacement is None:
            break
        current = replacement
        fixed = True
        iterations += 1
    return {"answer": current, "fixed": fixed, "iterations": iterations}
