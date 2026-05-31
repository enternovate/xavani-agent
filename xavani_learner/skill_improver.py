# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Skill Auto-Improvement Loop — Propose skill drafts from successful trajectories.

After a successful task trajectory (high pass rate on evals, user satisfaction,
or clean guidelines gate), this module can propose a draft SKILL.md that
captures the proven approach. Drafts go to ``~/.xavani/skill-drafts/`` for
human review — they are NEVER auto-written to ``skills/``.

Design:
  1. Observe: detect when a task completes successfully.
  2. Extract: identify the reusable pattern from the trajectory.
  3. Propose: generate a draft SKILL.md in the standard format.
  4. Review: human approves, edits, or discards the draft.
  5. Promote: approved drafts move to ``skills/`` or ``~/.xavani/skills/``.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from xavani_cli.safe_logging import SafeLogFilter
    SafeLogFilter.install()
except Exception:
    pass


# ---------------------------------------------------------------------------
# Draft storage
# ---------------------------------------------------------------------------


def _draft_dir() -> Path:
    """Return the skill drafts directory."""
    from xavani_constants import get_xavani_home
    d = get_xavani_home() / "skill-drafts"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _draft_path(name: str) -> Path:
    """Return the path to a draft file."""
    safe_name = name.replace("/", "_").replace("\\", "_").replace("..", "_")
    return _draft_dir() / f"{safe_name}.md"


# ---------------------------------------------------------------------------
# Pattern extraction
# ---------------------------------------------------------------------------


def extract_pattern_from_trajectory(
    task_description: str,
    steps_taken: List[str],
    tools_used: List[str],
    outcome: str,
    eval_pass_rate: float = 0.0,
) -> Dict[str, Any]:
    """Extract a reusable pattern from a successful trajectory.

    Returns a structured pattern that can be turned into a SKILL.md.
    """
    # Determine the category based on tools used
    category = "general"
    tool_categories = {
        "terminal": "devops",
        "read_file": "software-development",
        "write_file": "software-development",
        "patch": "software-development",
        "search_files": "software-development",
        "web_search": "research",
        "eval_harness": "testing",
        "guidelines_gate": "quality",
    }
    for tool in tools_used:
        if tool in tool_categories:
            category = tool_categories[tool]
            break

    # Build the pattern
    pattern = {
        "name": _generate_skill_name(task_description),
        "description": f"Pattern extracted from: {task_description[:100]}",
        "category": category,
        "trigger": task_description[:200],
        "steps": steps_taken,
        "tools": tools_used,
        "outcome": outcome,
        "eval_pass_rate": eval_pass_rate,
        "extracted_at": time.time(),
    }
    return pattern


def _generate_skill_name(task_description: str) -> str:
    """Generate a kebab-case skill name from a task description."""
    import re
    # Take first 5 words, lowercase, replace spaces with hyphens
    words = task_description.lower().split()[:5]
    name = "-".join(words)
    # Remove non-alphanumeric chars except hyphens
    name = re.sub(r"[^a-z0-9-]", "", name)
    # Collapse multiple hyphens
    name = re.sub(r"-+", "-", name).strip("-")
    return name or "unnamed-skill"


# ---------------------------------------------------------------------------
# Draft generation
# ---------------------------------------------------------------------------


def propose_skill_draft(
    pattern: Dict[str, Any],
    force: bool = False,
) -> Dict[str, Any]:
    """Generate a draft SKILL.md from an extracted pattern.

    The draft is saved to ``~/.xavani/skill-drafts/`` for human review.
    Never auto-writes to ``skills/``.
    """
    name = pattern.get("name", "unnamed-skill")
    draft_path = _draft_path(name)

    if draft_path.exists() and not force:
        return {
            "ok": False,
            "message": f"Draft '{name}' already exists. Use force=True to overwrite.",
            "path": str(draft_path),
        }

    # Build the SKILL.md content
    steps_text = "\n".join(f"{i+1}. {step}" for i, step in enumerate(pattern.get("steps", [])))
    tools_text = ", ".join(pattern.get("tools", []))

    content = f"""---
name: {name}
description: {pattern.get('description', 'Auto-generated skill draft')}
categories:
  - {pattern.get('category', 'general')}
platforms:
  - all
tags:
  - auto-generated
  - draft
condition: When performing tasks similar to: {pattern.get('trigger', 'N/A')[:100]}
---

# {name.replace('-', ' ').title()}

> Auto-generated from a successful trajectory. Review and refine before promoting.

## When to use

{pattern.get('trigger', 'Describe when to use this skill.')}

## Steps

{steps_text}

## Tools used

{tools_text}

## Outcome

{pattern.get('outcome', 'Describe the expected outcome.')}

## Verification

- Eval pass rate from original trajectory: {pattern.get('eval_pass_rate', 0):.1f}%
- Review the steps above and verify they generalize.
- Add concrete examples before promoting to production.

## Status

**DRAFT** — Requires human review before use.
Generated at: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(pattern.get('extracted_at', time.time())))}
"""

    draft_path.write_text(content, encoding="utf-8")

    return {
        "ok": True,
        "message": f"Draft skill '{name}' proposed at {draft_path}",
        "path": str(draft_path),
        "name": name,
    }


# ---------------------------------------------------------------------------
# Draft management
# ---------------------------------------------------------------------------


def list_drafts() -> List[Dict[str, Any]]:
    """List all pending skill drafts."""
    drafts = []
    for path in sorted(_draft_dir().glob("*.md")):
        try:
            content = path.read_text(encoding="utf-8")
            # Extract name from frontmatter
            name = path.stem
            if content.startswith("---"):
                for line in content.split("\n")[1:]:
                    if line.startswith("name:"):
                        name = line.split(":", 1)[1].strip()
                        break
            drafts.append({
                "name": name,
                "path": str(path),
                "size": path.stat().st_size,
            })
        except Exception:
            continue
    return drafts


def approve_draft(name: str, target_dir: Optional[str] = None) -> Dict[str, Any]:
    """Approve a draft and promote it to skills/.

    If target_dir is specified, moves the draft there.
    Otherwise moves to ~/.xavani/skills/.
    """
    draft_path = _draft_path(name)
    if not draft_path.exists():
        return {"ok": False, "message": f"Draft '{name}' not found."}

    if target_dir:
        dest = Path(target_dir) / name / "SKILL.md"
    else:
        from xavani_constants import get_xavani_home
        dest = get_xavani_home() / "skills" / name / "SKILL.md"

    dest.parent.mkdir(parents=True, exist_ok=True)

    # Update the status in the content
    content = draft_path.read_text(encoding="utf-8")
    content = content.replace("**DRAFT**", "**ACTIVE**")
    content = content.replace("Requires human review before use.", "Approved and promoted.")
    dest.write_text(content, encoding="utf-8")

    # Remove the draft
    draft_path.unlink()

    return {"ok": True, "message": f"Skill '{name}' promoted to {dest}", "path": str(dest)}


def discard_draft(name: str) -> Dict[str, Any]:
    """Discard a skill draft."""
    draft_path = _draft_path(name)
    if not draft_path.exists():
        return {"ok": False, "message": f"Draft '{name}' not found."}
    draft_path.unlink()
    return {"ok": True, "message": f"Draft '{name}' discarded."}
