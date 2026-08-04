# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""D14: prompt injection detection — known-pattern matching.

Detects KNOWN injection patterns in untrusted text (tool results, web
content, file contents, gateway metadata):

- explicit instruction overrides ("ignore previous instructions")
- role confusion ("you are now", "act as", "new system prompt")
- information exfiltration lures ("repeat your instructions")
- jailbreak templates ("DAN", "developer mode", "freedom prompt")

This is pattern matching against known attacks, NOT general semantic
detection — that problem is unsolved, and claiming otherwise would be a
security lie. Detection is advisory: it logs the attempt and returns a
verdict; it never silently mutates content. Callers decide the policy
(warn, sanitize, or block).

Usage::

    from agent.prompt_guard import scan_text

    verdict = scan_text(untrusted_tool_output)
    if verdict.flagged:
        logger.warning("possible injection: %s", verdict.rule_id)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)

# (rule_id, regex, description) — ordered; all matches are reported.
_INJECTION_RULES: List[tuple[str, re.Pattern, str]] = [
    (
        "instruction_override",
        re.compile(
            r"ignore (?:all |the )?(?:previous|prior|above|earlier) "
            r"(?:instructions?|prompts?|messages?|context)",
            re.IGNORECASE,
        ),
        "explicit instruction override",
    ),
    (
        "role_confusion",
        re.compile(
            r"\b(?:you are (?:now|not )?(?:an? |the )?(?:system|assistant|ai|gpt)"
            r"|act as (?:an? |the )?(?:system|assistant|ai|gpt))",
            re.IGNORECASE,
        ),
        "role confusion / system impersonation",
    ),
    (
        "new_system_prompt",
        re.compile(
            r"(?:new|reset|replace).{0,20}(?:system prompt|system message|instructions?)",
            re.IGNORECASE,
        ),
        "attempt to redefine the system prompt",
    ),
    (
        "exfiltration_lure",
        re.compile(
            r"(?:repeat|print|output|reveal|show|disclose|paste).{0,20}"
            r"(?:your (?:system |initial )?(?:instructions?|prompt|message))",
            re.IGNORECASE,
        ),
        "attempt to extract the system prompt",
    ),
    (
        "jailbreak_dan",
        re.compile(
            r"\b(?:DAN(?: mode)?|developer mode|jailbreak|freedom prompt|"
            r"do anything now)\b",
            re.IGNORECASE,
        ),
        "known jailbreak template",
    ),
    (
        "delimiter_breakout",
        re.compile(
            r"(?:end (?:the )?(?:conversation|turn|message)|"
            r"disregard (?:the )?(?:delimiter|separator|format))",
            re.IGNORECASE,
        ),
        "attempt to break out of the message boundary",
    ),
]


@dataclass
class ScanVerdict:
    """Result of scanning untrusted text for injection patterns."""

    flagged: bool
    rule_ids: List[str] = field(default_factory=list)
    descriptions: List[str] = field(default_factory=list)

    @property
    def first_rule(self) -> Optional[str]:
        return self.rule_ids[0] if self.rule_ids else None


def scan_text(text: str) -> ScanVerdict:
    """Scan untrusted text for known injection patterns.

    Returns a verdict with every matching rule. Never raises.
    """
    if not text:
        return ScanVerdict(flagged=False)
    flagged = False
    rule_ids: List[str] = []
    descriptions: List[str] = []
    for rule_id, pattern, description in _INJECTION_RULES:
        if pattern.search(text):
            flagged = True
            rule_ids.append(rule_id)
            descriptions.append(description)
    return ScanVerdict(flagged=flagged, rule_ids=rule_ids, descriptions=descriptions)


def log_attempt(verdict: ScanVerdict, source: str = "unknown", sample: str = "") -> None:
    """Log a detected injection attempt (advisory — never raises)."""
    if not verdict.flagged:
        return
    try:
        logger.warning(
            "Possible prompt injection from %s: %s (sample: %.120r)",
            source,
            ", ".join(verdict.rule_ids),
            sample,
        )
    except Exception:
        pass
