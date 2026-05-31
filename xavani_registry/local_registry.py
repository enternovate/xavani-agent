# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Local Skill Registry v2 — safe, audited skill discovery.

Scans ``skills/``, ``optional-skills/``, and ``~/.xavani/skills/`` for
SKILL.md files. Provides:
  * ``scan_all_skills()`` — discover all skills with frontmatter metadata.
  * ``add_skill_by_path(path)`` — validate and add a skill from an arbitrary path.
  * ``list_skills()`` — return all discovered skills.
  * ``get_skill(name)`` — look up a skill by name.

Safety:
  * Validates frontmatter before accepting.
  * Enforces unique ``name`` (rejects duplicates).
  * Runs a scrub check (no prohibited brand references) before accepting.
  * No network crawler — discovery is local-only.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from xavani_constants import get_skills_dir

logger = logging.getLogger(__name__)

try:
    from xavani_cli.safe_logging import SafeLogFilter
    SafeLogFilter.install()
except Exception:
    pass

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REQUIRED_FRONTMATTER = ("name", "description")
# Scrub pattern — reuse from the guidelines gate to avoid duplicating
# prohibited brand references in this module.
try:
    from tools.guidelines_gate_tool import _SCRUB_PATTERN
except ImportError:
    # Defensive fallback if the gate tool isn't available
    import re as _re
    _SCRUB_PATTERN = _re.compile(r"(?i)\b(nous|hermes[-_]?agent)\b")
EXCLUDED_DIRS = frozenset((".git", ".github", ".hub", ".archive", "__pycache__", "node_modules"))

# ---------------------------------------------------------------------------
# Frontmatter parsing (reuses agent/skill_utils)
# ---------------------------------------------------------------------------


def _parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Parse YAML frontmatter from a SKILL.md file."""
    try:
        from agent.skill_utils import parse_frontmatter
        return parse_frontmatter(content)
    except ImportError:
        # Fallback: simple regex split
        if not content.startswith("---"):
            return {}, content
        end = content.find("\n---", 3)
        if end == -1:
            return {}, content
        try:
            import yaml
            fm = yaml.safe_load(content[4:end]) or {}
        except Exception:
            fm = {}
        body = content[end + 4:].strip()
        return fm if isinstance(fm, dict) else {}, body


def _scrub_check(text: str) -> List[str]:
    """Check for prohibited brand references. Returns list of violations."""
    violations = []
    for i, line in enumerate(text.splitlines(), 1):
        if _SCRUB_PATTERN.search(line):
            violations.append(f"Line {i}: {line.strip()[:100]}")
    return violations


# ---------------------------------------------------------------------------
# Skill scanning
# ---------------------------------------------------------------------------


def _walk_skill_dirs() -> List[Path]:
    """Return all directories that may contain skills."""
    dirs = []

    # Built-in skills
    repo_root = Path(__file__).resolve().parent.parent
    skills_dir = repo_root / "skills"
    if skills_dir.is_dir():
        dirs.append(skills_dir)

    # Optional skills
    optional_dir = repo_root / "optional-skills"
    if optional_dir.is_dir():
        dirs.append(optional_dir)

    # User skills
    user_skills = get_skills_dir()
    if user_skills.is_dir():
        dirs.append(user_skills)

    return dirs


def _discover_skill_files(base_dir: Path) -> List[Path]:
    """Recursively find all SKILL.md files under base_dir."""
    matches = []
    for skill_path in base_dir.rglob("SKILL.md"):
        # Skip excluded directories
        parts = skill_path.relative_to(base_dir).parts
        if any(p in EXCLUDED_DIRS for p in parts[:-1]):
            continue
        matches.append(skill_path)
    return sorted(matches)


def _load_skill_metadata(skill_path: Path) -> Optional[Dict[str, Any]]:
    """Load and validate a single SKILL.md file."""
    try:
        content = skill_path.read_text(encoding="utf-8")
    except OSError:
        return None

    fm, body = _parse_frontmatter(content)
    if not fm:
        return None

    # Validate required fields
    for field in REQUIRED_FRONTMATTER:
        if field not in fm:
            logger.debug("Skipping %s: missing required field '%s'", skill_path, field)
            return None

    # Scrub check
    violations = _scrub_check(content)
    if violations:
        logger.warning("Scrub violations in %s: %s", skill_path, violations)
        return None

    return {
        "name": str(fm["name"]),
        "description": str(fm.get("description", "")),
        "categories": fm.get("categories", []),
        "platforms": fm.get("platforms", []),
        "tags": fm.get("tags", []),
        "condition": fm.get("condition", ""),
        "path": str(skill_path),
        "body_preview": body[:200] if body else "",
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_registry_cache: Optional[Dict[str, Dict[str, Any]]] = None
_cache_lock = threading.Lock()


def scan_all_skills(*, reload: bool = False) -> Dict[str, Dict[str, Any]]:
    """Scan all skill directories and return {name: metadata}.

    Results are cached after the first call. Pass ``reload=True`` to re-scan.
    """
    global _registry_cache
    with _cache_lock:
        if _registry_cache is not None and not reload:
            return _registry_cache

        registry: Dict[str, Dict[str, Any]] = {}
        for base_dir in _walk_skill_dirs():
            for skill_path in _discover_skill_files(base_dir):
                meta = _load_skill_metadata(skill_path)
                if meta is None:
                    continue
                name = meta["name"]
                if name in registry:
                    logger.warning(
                        "Duplicate skill name '%s': %s conflicts with %s",
                        name, skill_path, registry[name]["path"],
                    )
                    continue
                registry[name] = meta

        _registry_cache = registry
        return _registry_cache


def list_skills() -> List[Dict[str, Any]]:
    """Return all discovered skills as a list."""
    return list(scan_all_skills().values())


def get_skill(name: str) -> Optional[Dict[str, Any]]:
    """Look up a skill by name."""
    return scan_all_skills().get(name)


def add_skill_by_path(path: str) -> Dict[str, Any]:
    """Validate and add a skill from an arbitrary path.

    Returns {"ok": True, "name": ...} on success, {"error": ...} on failure.
    """
    skill_path = Path(path).resolve()
    if not skill_path.exists():
        return {"error": f"Path does not exist: {path}"}

    if skill_path.is_dir():
        # Look for SKILL.md inside
        skill_path = skill_path / "SKILL.md"
        if not skill_path.exists():
            return {"error": f"No SKILL.md found in {path}"}

    meta = _load_skill_metadata(skill_path)
    if meta is None:
        return {"error": f"Failed to parse or validate {skill_path}"}

    # Check for duplicate
    registry = scan_all_skills()
    if meta["name"] in registry:
        existing = registry[meta["name"]]
        if str(skill_path) != existing["path"]:
            return {"error": f"Skill '{meta['name']}' already exists at {existing['path']}"}

    # Add to cache
    with _cache_lock:
        if _registry_cache is not None:
            _registry_cache[meta["name"]] = meta

    return {"ok": True, "name": meta["name"], "path": str(skill_path)}


def invalidate_cache() -> None:
    """Clear the registry cache. Call after adding/removing skills."""
    global _registry_cache
    with _cache_lock:
        _registry_cache = None
