# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Loader for the mandatory research-guideline pack.

The pack lives at ``skills/research-guidelines/`` and contains one
``<thinker>-guidelines.md`` file per principle source plus a
``MANIFEST.md`` index. Each guideline file is markdown with a YAML
frontmatter block describing ``name``, ``description``, ``domain``,
``mandatory``, ``priority``, ``version``, and citation ``sources``.

This module:

* discovers the files at startup,
* parses + validates their frontmatter,
* sorts them by priority (descending; alphabetic tie-break),
* exposes a condensed system-prompt block for injection into
  :data:`xavani_cli.default_soul.DEFAULT_SOUL_MD`,
* and exposes the full bodies for on-demand consultation.

It is deliberately read-only and dependency-light. The only third-party
dependency is PyYAML, which is already a hard requirement of the rest of
the CLI; if PyYAML is missing the loader falls back to an empty list and
logs a single warning instead of crashing the agent.
"""

from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from xavani_cli.safe_logging import install as _install_safe_logging

    _install_safe_logging()
except Exception:  # pragma: no cover — defensive
    pass

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GUIDELINE_DIR_NAME: str = "research-guidelines"
"""Directory under ``skills/`` that holds the mandatory guideline pack."""

GUIDELINE_FILE_GLOB: str = "*-guidelines.md"
"""Glob pattern used to discover guideline files."""

REQUIRED_FRONTMATTER_FIELDS: Tuple[str, ...] = (
    "name",
    "description",
    "domain",
    "mandatory",
    "priority",
    "version",
)

# A small, regex-only frontmatter splitter so we don't have to depend on
# python-frontmatter. The pattern matches a leading ``---\n...\n---\n``
# block; everything after is treated as body. Designed to be liberal in
# what it accepts (CRLF, trailing whitespace) but strict in what it emits.
_FRONTMATTER_RE = re.compile(
    r"\A---\s*\r?\n(?P<frontmatter>.*?)\r?\n---\s*\r?\n?(?P<body>.*)\Z",
    re.DOTALL,
)

# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Guideline:
    """A parsed guideline file.

    Frozen because guidelines are read-once at startup and never
    mutated; the loader exposes them through a tuple so consumers
    can't accidentally rearrange the priority ordering.
    """

    name: str
    description: str
    domain: str
    mandatory: bool
    priority: int
    version: str
    sources: Tuple[str, ...]
    body: str
    path: Path
    raw_frontmatter: Dict[str, Any] = field(default_factory=dict)

    @property
    def headline(self) -> str:
        """Return the first non-empty body line (used in the condensed block)."""
        for line in self.body.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith(("#", ">", "---")):
                return stripped
        return self.description


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def _project_root() -> Path:
    """Return the repository root that contains ``skills/``."""
    return Path(__file__).resolve().parent.parent


def guideline_dir() -> Path:
    """Return the absolute path to the research-guidelines directory."""
    return _project_root() / "skills" / GUIDELINE_DIR_NAME


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def _parse_frontmatter(text: str, *, source: Path) -> Tuple[Dict[str, Any], str]:
    """Split ``text`` into (frontmatter dict, body)."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError(
            f"{source} is missing a YAML frontmatter block "
            f"(expected ``---\\n…\\n---``)"
        )

    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover — yaml is required by the CLI
        raise RuntimeError(
            "PyYAML is required to load the research guidelines pack"
        ) from exc

    try:
        data = yaml.safe_load(match.group("frontmatter")) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"{source} has invalid YAML frontmatter: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"{source} frontmatter must be a YAML mapping")

    missing = [f for f in REQUIRED_FRONTMATTER_FIELDS if f not in data]
    if missing:
        raise ValueError(
            f"{source} is missing required frontmatter fields: "
            + ", ".join(missing)
        )

    return data, match.group("body").lstrip("\n")


def _coerce_sources(value: Any) -> Tuple[str, ...]:
    """Normalise the ``sources`` field to a tuple of strings."""
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (list, tuple)):
        return tuple(str(v) for v in value)
    return (str(value),)


def _build_guideline(path: Path) -> Guideline:
    text = path.read_text(encoding="utf-8")
    data, body = _parse_frontmatter(text, source=path)

    priority = data.get("priority", 0)
    if not isinstance(priority, int):
        try:
            priority = int(priority)
        except (TypeError, ValueError):
            priority = 0

    return Guideline(
        name=str(data["name"]),
        description=str(data["description"]),
        domain=str(data["domain"]),
        mandatory=bool(data["mandatory"]),
        priority=priority,
        version=str(data["version"]),
        sources=_coerce_sources(data.get("sources")),
        body=body,
        path=path,
        raw_frontmatter=data,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


_cache_lock = threading.RLock()
_cached: Optional[Tuple[Guideline, ...]] = None


def load_mandatory_guidelines(*, reload: bool = False) -> Tuple[Guideline, ...]:
    """Return the priority-ordered tuple of mandatory guidelines.

    The result is cached after the first call. Pass ``reload=True`` to
    re-read the filesystem (useful in tests or after hot-editing a
    guideline file in development).
    """
    global _cached
    with _cache_lock:
        if _cached is not None and not reload:
            return _cached

        directory = guideline_dir()
        if not directory.is_dir():
            logger.warning(
                "Research-guidelines directory not found at %s; "
                "agent will run without the mandatory principle pack",
                directory,
            )
            _cached = ()
            return _cached

        items: List[Guideline] = []
        for path in sorted(directory.glob(GUIDELINE_FILE_GLOB)):
            try:
                guideline = _build_guideline(path)
            except (OSError, ValueError) as exc:
                logger.warning("Skipping malformed guideline %s: %s", path, exc)
                continue
            if not guideline.mandatory:
                continue
            items.append(guideline)

        # Priority descending, then alphabetical for stable tie-break.
        items.sort(key=lambda g: (-g.priority, g.name))
        _cached = tuple(items)
        return _cached


def compose_system_prompt_block(guidelines: Optional[Tuple[Guideline, ...]] = None) -> str:
    """Render the condensed system-prompt reference block.

    The block is intentionally small — one heading per guideline and a
    one-line summary — so it doesn't dominate the system prompt. The
    full body of any guideline can be read on demand via
    :func:`get_guideline`.
    """
    items = guidelines if guidelines is not None else load_mandatory_guidelines()
    if not items:
        return ""

    lines: List[str] = [
        "## Mandatory Research Guidelines (always-on)",
        "",
        "These principles govern how this agent reasons, builds, and ships.",
        "They are loaded into context in perpetuity by `xavani_cli."
        "research_guidelines`. Read the full file under "
        "`skills/research-guidelines/<name>-guidelines.md` whenever you "
        "hit one of the 'When to invoke' conditions.",
        "",
    ]
    for g in items:
        lines.append(f"### {g.name} ({g.domain}, priority {g.priority})")
        lines.append(f"_{g.description}_")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def get_guideline(name: str) -> Optional[Guideline]:
    """Return the guideline whose ``name`` matches ``name`` (case-insensitive)."""
    if not name:
        return None
    needle = name.strip().lower()
    for g in load_mandatory_guidelines():
        if g.name.lower() == needle:
            return g
    return None


def list_guideline_names() -> Tuple[str, ...]:
    """Return the names of all mandatory guidelines in priority order."""
    return tuple(g.name for g in load_mandatory_guidelines())


__all__ = [
    "Guideline",
    "GUIDELINE_DIR_NAME",
    "GUIDELINE_FILE_GLOB",
    "REQUIRED_FRONTMATTER_FIELDS",
    "compose_system_prompt_block",
    "get_guideline",
    "guideline_dir",
    "list_guideline_names",
    "load_mandatory_guidelines",
]
