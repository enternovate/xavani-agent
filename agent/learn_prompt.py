# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""B04: learn prompt pack (``/learn``).

Turns a user correction into a durable skill draft.  Extraction is
deterministic and offline: explicit ``rule:`` / ``example:`` markers
win; otherwise the first sentence becomes the rule and the rest the
example.  Drafts land in ``<XAVANI_HOME>/pending/skills/`` — the same
staging store the write-approval gate uses — so a human can review
before a draft ever becomes a live skill.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_MARKER_RE = re.compile(r"^\s*(title|rule|example)\s*:\s*(.*)$", re.IGNORECASE)
_SLUG_RE = re.compile(r"[^a-z0-9]+")


@dataclass
class LearnDraft:
    """A proposed skill derived from a user correction."""

    title: str
    rule: str
    example: str = ""
    source: str = ""


def _default_title(correction: str) -> str:
    words = _SLUG_RE.sub(" ", correction.lower()).split()
    return " ".join(words[:6]) or "learned-rule"


def extract_learn_draft(correction: str, source: str = "") -> LearnDraft:
    """Extract title/rule/example from a correction string."""
    correction = (correction or "").strip()
    if not correction:
        return LearnDraft(title="", rule="", source=source)

    title = ""
    rule = ""
    example = ""
    body: list[str] = []
    for line in correction.splitlines():
        match = _MARKER_RE.match(line)
        if match:
            key, value = match.group(1).lower(), match.group(2).strip()
            if key == "title":
                title = value
            elif key == "rule":
                rule = value
            elif key == "example":
                example = value
            continue
        if line.strip():
            body.append(line.strip())

    if not rule and body:
        # First sentence is the rule; the rest is the example.
        first = body[0]
        sentence_end = re.search(r"[.!?](?:\s|$)", first)
        if sentence_end:
            rule = first[: sentence_end.end()].strip()
            example = (first[sentence_end.end() :].strip() + " " + " ".join(body[1:])).strip()
        else:
            rule = first
            example = " ".join(body[1:])
    if not example and len(body) > 1:
        example = " ".join(body[1:])
    if not title:
        title = _default_title(rule or correction)
    return LearnDraft(title=title, rule=rule, example=example, source=source)


def render_skill_draft(draft: LearnDraft) -> str:
    """Render the draft as a SKILL.md file body."""
    name = _SLUG_RE.sub("-", draft.title.lower()).strip("-") or "learned-rule"
    lines = [
        "---",
        f"name: {name}",
        "description: Learned rule (draft — review before publishing).",
        "---",
        "",
        f"# {draft.title}",
        "",
        "## Rule",
        "",
        draft.rule,
    ]
    if draft.example:
        lines += ["", "## Example", "", draft.example]
    if draft.source:
        lines += ["", f"Source: {draft.source}"]
    return "\n".join(lines) + "\n"


def save_skill_draft(draft: LearnDraft, home: Optional[Path] = None) -> Path:
    """Write the draft into the pending-skills staging store."""
    base = home if home is not None else Path(
        os.environ.get("XAVANI_HOME", "~/.xavani")
    ).expanduser()
    target_dir = base / "pending" / "skills"
    target_dir.mkdir(parents=True, exist_ok=True)
    name = _SLUG_RE.sub("-", draft.title.lower()).strip("-") or "learned-rule"
    target = target_dir / f"{name}.md"
    target.write_text(render_skill_draft(draft), encoding="utf-8")
    return target


def learn_from_correction(correction: str, source: str = "") -> dict:
    """Full pipeline: extract, render, stage. Returns the draft dict."""
    draft = extract_learn_draft(correction, source=source)
    if not draft.rule:
        return {"ok": False, "draft": draft, "markdown": "", "path": None}
    path = save_skill_draft(draft)
    return {
        "ok": True,
        "draft": draft,
        "markdown": render_skill_draft(draft),
        "path": str(path),
    }
