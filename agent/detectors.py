# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Deterministic detector registry (v0.4.0 roadmap U9).

A single place to register and run pure-Python "detectors" — the checks the
agent makes about its own work **without** an LLM (R10): scrub (no upstream
references), service-guard (no prohibited default service hosts), and a
secret-leak heuristic. Each detector takes a ``context`` dict and returns a
:class:`Verdict`.

This module imports **no** model client and performs no network or file I/O; it
operates only on the strings handed to it (``text`` / ``diff``). It is the
deterministic backbone the guidelines gate, the ``xavani`` CLI, and CI can all
share without spending a single token.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List


@dataclass
class Verdict:
    """Result of running one detector."""

    detector: str
    ok: bool
    findings: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


Detector = Callable[[Dict[str, Any]], Verdict]

_REGISTRY: Dict[str, Detector] = {}


def register(name: str, fn: Detector) -> None:
    """Register a detector under ``name`` (idempotent overwrite)."""
    _REGISTRY[name] = fn


def get(name: str) -> Detector | None:
    return _REGISTRY.get(name)


def names() -> List[str]:
    """Registered detector names, sorted for deterministic iteration."""
    return sorted(_REGISTRY)


def run(name: str, context: Dict[str, Any]) -> Verdict:
    detector = _REGISTRY.get(name)
    if detector is None:
        raise KeyError(f"no detector named {name!r}")
    return detector(context)


def run_all(context: Dict[str, Any]) -> List[Verdict]:
    """Run every registered detector (deterministic order) and return verdicts."""
    return [_REGISTRY[name](context) for name in sorted(_REGISTRY)]


def _text_of(context: Dict[str, Any]) -> str:
    return str(context.get("text") or context.get("diff") or "")


# ── Built-in deterministic detectors ──────────────────────────────────────────

_SCRUB_RE = re.compile(r"(?i)\b(nous|hermes[-_]?agent)\b")
_SERVICE_HOSTS_FALLBACK = ("nousresearch.com",)
_SECRET_PATTERNS = (
    (r"sk-[A-Za-z0-9]{20,}", "OpenAI-style API key"),
    (r"AKIA[0-9A-Z]{16}", "AWS access key id"),
    (r"gh[pousr]_[A-Za-z0-9]{30,}", "GitHub token"),
    (r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", "private key"),
)


def _detect_scrub(context: Dict[str, Any]) -> Verdict:
    """Flag any upstream-brand reference in the supplied text/diff."""
    text = _text_of(context)
    hits = sorted({m.group(0) for m in _SCRUB_RE.finditer(text)})
    return Verdict(
        detector="scrub",
        ok=not hits,
        findings=[f"upstream reference present: {h!r}" for h in hits],
    )


def _prohibited_hosts_in(text: str) -> List[str]:
    """Hosts from the Task 24a boundary list that ``text`` references."""
    try:
        from scripts.check_product_boundary import host_of, is_prohibited_host
    except ImportError:  # installed layouts may not ship scripts/
        from urllib.parse import urlsplit

        def host_of(url: str) -> str:
            try:
                return (urlsplit(url).hostname or "").lower()
            except ValueError:
                return ""

        def is_prohibited_host(host: str) -> bool:
            host = (host or "").lower()
            return any(
                host == apex or host.endswith("." + apex)
                for apex in _SERVICE_HOSTS_FALLBACK
            )

    hits = set()
    for match in re.finditer(r"https?://[^\s\"'`<>)\]}]+", text):
        host = host_of(match.group(0))
        if is_prohibited_host(host):
            hits.add(host)
    return sorted(hits)


def _detect_service_guard(context: Dict[str, Any]) -> Verdict:
    """Flag a diff that introduces a prohibited default service host (Task 24a).

    Behavioral replacement for the removed stub path ban: the modules once
    treated as permanent stubs are implemented and shipped, so the guard
    now checks the property that matters — no upstream subscription or
    portal host may enter the tree.
    """
    diff = str(context.get("diff") or "")
    added = "\n".join(line for line in diff.splitlines() if line.startswith("+"))
    hits = _prohibited_hosts_in(added)
    return Verdict(
        detector="service_guard",
        ok=not hits,
        findings=[f"prohibited service host referenced: {h}" for h in hits],
    )


def _detect_secret_leak(context: Dict[str, Any]) -> Verdict:
    """Heuristic scan for committed secrets (deterministic, no entropy model)."""
    text = _text_of(context)
    findings = [label for pattern, label in _SECRET_PATTERNS if re.search(pattern, text)]
    return Verdict(
        detector="secret_leak",
        ok=not findings,
        findings=[f"possible secret: {f}" for f in findings],
    )


for _name, _fn in (
    ("scrub", _detect_scrub),
    ("service_guard", _detect_service_guard),
    ("secret_leak", _detect_secret_leak),
):
    register(_name, _fn)


__all__ = ["Verdict", "Detector", "register", "get", "names", "run", "run_all"]
