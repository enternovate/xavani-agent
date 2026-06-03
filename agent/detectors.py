# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Deterministic detector registry (v0.4.0 roadmap U9).

A single place to register and run pure-Python "detectors" — the checks the
agent makes about its own work **without** an LLM (R10): scrub (no upstream
references), stub-guard (deliberate stubs untouched), and a secret-leak
heuristic. Each detector takes a ``context`` dict and returns a :class:`Verdict`.

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
_STUB_FILES = ("tools/skills_hub.py", "gateway/platforms/weixin.py")
_SECRET_PATTERNS = (
    (r"sk-[A-Za-z0-9]{20,}", "OpenAI-style API key"),
    (r"AKIA[0-9A-Z]{16}", "AWS access key id"),
    (r"gh[pousr]_[A-Za-z0-9]{30,}", "GitHub token"),
    (r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", "private key"),
)


def _detect_scrub(context: Dict[str, Any]) -> Verdict:
    """Flag any upstream (Nous/Hermes) reference in the supplied text/diff."""
    text = _text_of(context)
    hits = sorted({m.group(0) for m in _SCRUB_RE.finditer(text)})
    return Verdict(
        detector="scrub",
        ok=not hits,
        findings=[f"upstream reference present: {h!r}" for h in hits],
    )


def _detect_stub_guard(context: Dict[str, Any]) -> Verdict:
    """Flag a diff that modifies the deliberate stub modules (R2)."""
    diff = str(context.get("diff") or "")
    touched = [f for f in _STUB_FILES if f in diff]
    return Verdict(
        detector="stub_guard",
        ok=not touched,
        findings=[f"deliberate stub modified: {f}" for f in touched],
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
    ("stub_guard", _detect_stub_guard),
    ("secret_leak", _detect_secret_leak),
):
    register(_name, _fn)


__all__ = ["Verdict", "Detector", "register", "get", "names", "run", "run_all"]
