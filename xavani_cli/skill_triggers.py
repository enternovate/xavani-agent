# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Skill auto-load triggers: a ``condition:`` frontmatter field.

Condition grammar (all optional, AND-combined):
- ``cwd-contains:<fragment>`` — current working directory contains fragment
- ``env:<NAME>=<value>`` — environment variable equals value
- ``file-exists:<relative path>`` — path exists under the cwd

Every evaluation is appended to ``~/.xavani/logs/skill_triggers.log``
with the decision, so auto-loading stays auditable.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


def parse_condition(frontmatter: Dict[str, Any]) -> Optional[List[str]]:
    """Extract condition clauses; None when no condition is declared."""
    raw = frontmatter.get("condition")
    if isinstance(raw, str) and raw.strip():
        return [c.strip() for c in raw.split(";") if c.strip()]
    if isinstance(raw, list) and raw:
        return [str(c).strip() for c in raw if str(c).strip()]
    return None


def evaluate_clause(clause: str, *, cwd: Path, env: Dict[str, str]) -> bool:
    """Evaluate one clause against cwd/env/file state."""
    kind, _, value = clause.partition(":")
    kind = kind.strip().lower()
    value = value.strip()
    if kind == "cwd-contains":
        return value.lower() in str(cwd).lower()
    if kind == "env":
        name, _, expected = value.partition("=")
        return os.getenv(name.strip(), "") == expected.strip()
    if kind == "file-exists":
        return (cwd / value).exists()
    return False


def should_autoload(
    frontmatter: Dict[str, Any],
    *,
    cwd: Optional[Path] = None,
    env: Optional[Dict[str, str]] = None,
) -> bool:
    """True when every declared condition holds (or none declared)."""
    clauses = parse_condition(frontmatter)
    if not clauses:
        return False
    cwd = cwd or Path.cwd()
    env = env or dict(os.environ)
    return all(evaluate_clause(c, cwd=cwd, env=env) for c in clauses)


def log_evaluation(
    skill_name: str,
    loaded: bool,
    *,
    reason: str = "",
    log_path: Optional[Path] = None,
) -> None:
    """Append one audit line per evaluation attempt."""
    target = log_path or (
        Path.home() / ".xavani" / "logs" / "skill_triggers.log"
    )
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y-%m-%dT%H:%M:%S")
        detail = f" reason={reason}" if reason else ""
        with open(target, "a", encoding="utf-8") as fh:
            fh.write(f"{stamp} skill={skill_name} autoload={loaded}{detail}\n")
    except OSError:
        pass


def evaluate_skill(
    skill_name: str,
    frontmatter: Dict[str, Any],
    *,
    cwd: Optional[Path] = None,
    env: Optional[Dict[str, str]] = None,
    log_path: Optional[Path] = None,
) -> bool:
    """Evaluate one skill's trigger and record the audit line."""
    clauses = parse_condition(frontmatter)
    loaded = should_autoload(frontmatter, cwd=cwd, env=env)
    reason = ";".join(clauses) if clauses else "no-condition"
    log_evaluation(skill_name, loaded, reason=reason, log_path=log_path)
    return loaded


def read_condition_from_skill(path: Path) -> Optional[List[str]]:
    """Read just the condition field from a SKILL.md file."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    block = text[3:end]
    for line in block.splitlines():
        if line.lower().startswith("condition:"):
            value = line.split(":", 1)[1].strip()
            return [c.strip() for c in value.split(";") if c.strip()] or None
    return None
