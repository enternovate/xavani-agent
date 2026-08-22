# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""
Import rules from other AI agents' config formats into xavani skill entries.

Supported sources (auto-detected by filename):

- ``CLAUDE.md`` / ``AGENTS.md`` — markdown; bullet/numbered list items and
  single-line paragraphs under headings become candidate rules. Code fences
  are skipped entirely, headings themselves are not rules, and markdown
  emphasis markers are stripped from rule-text edges.
- ``.cursorrules`` / ``.windsurfrules`` — plain text, one rule per non-empty
  line; lines starting with ``#`` are comments.

Every imported rule carries a provenance comment recording the source path
and import date so downstream consumers can trace where a rule came from.
"""

from __future__ import annotations

import datetime
import re
from pathlib import Path

MAX_RULE_LENGTH = 300
MAX_SLUG_LENGTH = 40

_MARKDOWN_SOURCE_NAMES = {"CLAUDE.md", "AGENTS.md"}
_PLAINTEXT_SOURCE_NAMES = {".cursorrules", ".windsurfrules"}

_HEADING_RE = re.compile(r"^#{1,6}\s+")
_LIST_ITEM_RE = re.compile(r"^(?:[-*+]|\d+[.)])\s+")
_FENCE_RE = re.compile(r"^(```|~~~)")
_EMPHASIS_EDGE_RE = re.compile(r"^[*_`]+|[*_`]+$")
_EMPHASIS_PAIRED_RE = re.compile(r"(\*\*|__|``|\*|_|`)([^*_`\n]+)\1")
_WHITESPACE_RUN_RE = re.compile(r"\s+")


def _strip_emphasis(text: str) -> str:
    """Strip paired markdown emphasis anywhere plus stray edge markers."""
    stripped = _EMPHASIS_PAIRED_RE.sub(r"\2", text)
    return _EMPHASIS_EDGE_RE.sub("", stripped)


def detect_format(path: str) -> str:
    """Return the source format for *path*.

    Returns ``"markdown"`` for CLAUDE.md / AGENTS.md files and
    ``"plaintext"`` for .cursorrules / .windsurfrules files. Raises
    :class:`ValueError` for any unsupported filename.
    """
    name = Path(path).name
    if name in _MARKDOWN_SOURCE_NAMES:
        return "markdown"
    if name in _PLAINTEXT_SOURCE_NAMES:
        return "plaintext"
    raise ValueError(f"Unsupported config format: {path!r}")


def _parse_markdown(text: str) -> list[str]:
    """Extract candidate rules from markdown text."""
    rules: list[str] = []
    in_fence = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if in_fence:
            if _FENCE_RE.match(line):
                in_fence = False
            continue
        if _FENCE_RE.match(line):
            in_fence = True
            continue
        if not line or line.startswith("<!--") or _HEADING_RE.match(line):
            continue
        candidate = _LIST_ITEM_RE.sub("", line)
        rule = _strip_emphasis(candidate)
        if not rule:
            continue
        rules.append(rule)
    return rules


def _parse_plaintext(text: str) -> list[str]:
    """Extract one rule per non-empty, non-comment line."""
    rules: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        rules.append(line)
    return rules


def parse_rules(text: str, fmt: str) -> list[str]:
    """Parse *text* in format *fmt* into deduplicated rule strings.

    Order is preserved, empty rules are dropped, HTML comments (lines
    starting with ``<!--``) are skipped, internal whitespace runs collapse
    to single spaces, and each rule is truncated to 300 characters plus an
    ellipsis.
    """
    if fmt == "markdown":
        candidates = _parse_markdown(text)
    elif fmt == "plaintext":
        candidates = _parse_plaintext(text)
    else:
        raise ValueError(f"Unknown format: {fmt!r}")

    seen: set[str] = set()
    rules: list[str] = []
    for candidate in candidates:
        normalized = _WHITESPACE_RUN_RE.sub(" ", candidate).strip()
        if not normalized or normalized.startswith("<!--"):
            continue
        if len(normalized) > MAX_RULE_LENGTH:
            normalized = normalized[: MAX_RULE_LENGTH] + "..."
        if normalized in seen:
            continue
        seen.add(normalized)
        rules.append(normalized)
    return rules


def slugify(rule: str, index: int) -> str:
    """Build a unique slug for *rule*.

    The result is lowercase alnum-and-hyphen text capped at 40 characters,
    prefixed with ``rule-<index>`` so distinct rules always get distinct
    names.
    """
    stem = re.sub(r"[^a-z0-9]+", "-", rule.lower()).strip("-")
    budget = MAX_SLUG_LENGTH - len(f"rule-{index:03d}-")
    stem = stem[:budget].strip("-")
    return f"rule-{index:03d}-{stem}"


def to_skill_entries(rules: list[str], source_path: str) -> list[dict]:
    """Convert parsed rules into skill-entry dicts with provenance.

    Each entry is ``{"name": <slug>, "content": <rule + provenance
    comment>}``. The provenance comment records the source path and today's
    date.
    """
    today = datetime.date.today().isoformat()
    entries: list[dict] = []
    for index, rule in enumerate(rules):
        content = f"{rule}\n\n<!-- imported from {source_path} on {today} -->"
        entries.append({"name": slugify(rule, index), "content": content})
    return entries


def import_rules(source_path: str) -> list[dict]:
    """Read *source_path*, parse its rules, and return skill entries."""
    fmt = detect_format(source_path)
    text = Path(source_path).read_text(encoding="utf-8")
    return to_skill_entries(parse_rules(text, fmt), source_path)


def write_skills(entries: list[dict], out_dir: Path) -> tuple[list[Path], list[str]]:
    """Write skill entries under *out_dir*; never overwrite existing files.

    Returns ``(written_paths, skipped_names)`` so callers can surface
    entries that collided with files already on disk.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    skipped: list[str] = []
    for entry in entries:
        target = out_dir / f"{entry['name']}.md"
        if target.exists():
            skipped.append(entry["name"])
            continue
        body = (
            "---\n"
            f"name: {entry['name']}\n"
            f"description: Imported rule\n"
            "---\n"
            f"{entry['content']}\n"
        )
        target.write_text(body, encoding="utf-8")
        written.append(target)
    return written, skipped
