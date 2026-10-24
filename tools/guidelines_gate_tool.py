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
  * Prohibited services — diff introduces no prohibited default service:
    an upstream subscription/portal/telemetry host, telemetry enabled by
    default, an un-opted update check against a non-owned host, or a new
    network call to an undeclared host (R1 / Task 24a, Code Pack Q).

The former ``Stubs intact`` path ban on ``tools/skills_hub.py`` and
``gateway/platforms/weixin.py`` was removed: both modules are implemented and
shipped, so banning their paths blocked legitimate work. The behavioral rule
above replaces it.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Prohibited default services (Task 24a / Code Pack Q)
# ---------------------------------------------------------------------------

# One source of truth for the prohibited-host list: the Task 24a boundary
# scanner. ``tests/tools/test_guidelines_gate.py`` asserts the two sets match.
try:
    from scripts.check_product_boundary import (
        UPSTREAM_APEX_DOMAINS as PROHIBITED_APEX_DOMAINS,
        classify_host as _classify_host,
        host_of as _host_of,
        is_prohibited_host as _is_prohibited_host,
    )
except ImportError:  # installed layouts may not ship scripts/
    from urllib.parse import urlsplit as _urlsplit

    PROHIBITED_APEX_DOMAINS = frozenset({"nousresearch.com"})

    def _host_of(url: str) -> str:
        try:
            return (_urlsplit(url).hostname or "").lower()
        except ValueError:
            return ""

    def _is_prohibited_host(host: str) -> bool:
        host = (host or "").lower()
        return any(host == apex or host.endswith("." + apex) for apex in PROHIBITED_APEX_DOMAINS)

    _classify_host = None  # type: ignore[assignment]

#: Hosts a diff may call without discussion when the scanner is unavailable.
_ALLOWED_CALL_HOSTS = frozenset(
    {
        "enternovate.com",
        "www.enternovate.com",
        "enternovate.co.za",
        "www.enternovate.co.za",
    }
)

_URL_RE = re.compile(r"https?://[^\s\"'`<>\\)\]}]+")
_PROHIBITED_HOST_RE = re.compile(
    r"(?i)\b(?:[a-z0-9-]+\.)*(?:"
    + "|".join(re.escape(apex) for apex in sorted(PROHIBITED_APEX_DOMAINS))
    + r")\b"
)
_NETWORK_CALL_RE = re.compile(
    r"(?i)\b(?:requests|httpx|aiohttp|session)\.(?:get|post|put|patch|delete|head|request)\("
    r"|\burlopen\(|\burlretrieve\("
)
_DEFAULT_SERVICE_ENABLED_RE = re.compile(
    r"(?i)\b(?:telemetry|analytics|remote[_-]?inference|managed[_-]?tools"
    r"|check[_-]?for[_-]?updates|auto[_-]?update|update[_-]?checks?)\w*"
    r"\s*[:=]\s*(?:true|1|\"1\"|'1'|enabled)\b"
)
_SERVICE_DISABLED_RE = re.compile(
    r"(?i)(?:"
    r"\b(?:disable[sd]?|no|without|do[ _-]?not)[ _-]?"
    r"(?:track(?:ing)?|telemetry|analytics|updates?|inference|managed[ _-]?tools)\b"
    r"|\b(?:telemetry|analytics|remote[_-]?inference|managed[_-]?tools"
    r"|check[_-]?for[_-]?updates|auto[_-]?update|update[_-]?checks?)\w*"
    r"\s*[:=]\s*(?:false|0|\"0\"|'0'|off|disabled)\b"
    r"|\b(?:telemetry|analytics|remote[_-]?inference|managed[_-]?tools"
    r"|check[_-]?for[_-]?updates|auto[_-]?update|update[_-]?checks?)[_-]?disabled\b"
    r")"
)

#: Paths whose purpose is to contain these strings, or that are not product
#: surfaces. Legal files must retain upstream attribution; provider catalogs
#: list user-selected endpoints; guard modules and tests carry the detectors.
_EXEMPT_PATHS = frozenset(
    {
        "LICENSE",
        "THIRD_PARTY_NOTICES.md",
        "cli-config.yaml.example",
        "tools/guidelines_gate_tool.py",
        "xavani_registry/local_registry.py",
        "scripts/check_product_boundary.py",
    }
)
_EXEMPT_PREFIXES = ("tests/",)


def _is_exempt_path(path: str) -> bool:
    """True when this path is not a product surface for this rule."""
    if not path:
        return False
    if path in _EXEMPT_PATHS:
        return True
    return any(path.startswith(prefix) for prefix in _EXEMPT_PREFIXES)


def _host_is_declared(host: str) -> bool:
    """True when a new network call may target ``host`` unreviewed."""
    if not host:
        return True
    if _is_prohibited_host(host):
        return False
    if host in _ALLOWED_CALL_HOSTS:
        return True
    if _classify_host is None:
        return False
    return str(_classify_host(host)) not in {"undeclared", "prohibited"}


# ---------------------------------------------------------------------------
# Check implementations
# ---------------------------------------------------------------------------

_SCRUB_PATTERN = re.compile(r"(?i)\b(nous|hermes[-_]?agent)\b")


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


def _check_prohibited_services(diff_text: str) -> Dict[str, Any]:
    """Check that the diff introduces no prohibited default service.

    Behavioral replacement for the removed stub path ban (Task 24a, Code Pack
    Q). Fails on an upstream subscription/portal/telemetry host, an enabled
    default service, or an un-opted check against a non-owned host; warns on a
    new network call to an undeclared host.
    """
    current_file = ""
    failure: Optional[str] = None
    warning: Optional[str] = None

    for line in diff_text.splitlines():
        if line.startswith("diff --git"):
            parts = line.split()
            current_file = parts[3].lstrip("b/") if len(parts) >= 4 else ""
            continue
        if not line.startswith("+") or line.startswith("+++"):
            continue
        if _is_exempt_path(current_file):
            continue
        added = line[1:].strip()
        if not added:
            continue

        if _PROHIBITED_HOST_RE.search(added):
            failure = failure or (
                f"prohibited default service host: {added[:120]} (in {current_file or 'diff'})"
            )
            continue

        if _SERVICE_DISABLED_RE.search(added):
            continue

        if _DEFAULT_SERVICE_ENABLED_RE.search(added):
            failure = failure or f"enables a prohibited default service: {added[:120]}"
            continue

        if _NETWORK_CALL_RE.search(added):
            for match in _URL_RE.finditer(added):
                host = _host_of(match.group(0))
                if host and not _host_is_declared(host):
                    warning = warning or (
                        f"new network call targets an undeclared host '{host}' — declare "
                        f"it or drop it: {added[:120]}"
                    )
                    break

    if failure:
        return {"check": "prohibited_services", "status": "fail", "reason": failure}
    if warning:
        return {"check": "prohibited_services", "status": "warn", "reason": warning}
    return {"check": "prohibited_services", "status": "pass", "reason": ""}


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
        _check_prohibited_services(diff_text),
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
        "measurement stated, scrub (no prohibited brand references), "
        "prohibited services (no upstream subscription/portal/telemetry host, "
        "default telemetry, un-opted update target, or undeclared network call)."
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
