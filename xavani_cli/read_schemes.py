# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Read schemes: treat PRs, issues, and skills as readable paths.

``pr://owner/repo#123`` and ``issue://owner/repo#45`` read through the
GitHub REST API via ``gh api``. ``skill://name`` reads a built-in skill's
SKILL.md through the oag_skills index. Fetchers are injectable so tests
run without network or gh.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Callable, Dict, Optional

_SCHEME_RE = re.compile(r"^(pr|issue|skill)://(?P<rest>.*)$")
_REF_RE = re.compile(r"^(?P<repo>[\w.-]+/[\w.-]+)#(?P<number>\d+)$")


class SchemeError(ValueError):
    pass


def parse_scheme(path: str) -> Optional[Dict[str, str]]:
    """Parse pr://, issue://, or skill:// paths; None for other paths."""
    match = _SCHEME_RE.match(path.strip())
    if not match:
        return None
    scheme = match.group(1)
    rest = match.group("rest").strip()
    if scheme == "skill":
        if not rest:
            raise SchemeError("skill:// needs a skill name")
        return {"scheme": "skill", "name": rest}
    ref = _REF_RE.match(rest)
    if not ref:
        raise SchemeError(
            f"{scheme}:// expects owner/repo#number — got {rest!r}"
        )
    return {
        "scheme": scheme,
        "repo": ref.group("repo"),
        "number": ref.group("number"),
    }


def _gh_api(endpoint: str) -> str:
    result = subprocess.run(
        ["gh", "api", endpoint],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise SchemeError(f"gh api failed: {(result.stderr or '').strip()[:300]}")
    return result.stdout


def fetch_github(scheme: str, repo: str, number: str) -> str:
    """Fetch a PR diff+meta or an issue body through gh api."""
    if scheme == "pr":
        meta = json.loads(_gh_api(f"repos/{repo}/pulls/{number}"))
        diff = _gh_api(f"repos/{repo}/pulls/{number}.diff")
        return (
            f"# PR #{number}: {meta.get('title', '')}\n"
            f"state: {meta.get('state')} | author: {meta.get('user', {}).get('login')}\n\n"
            f"{meta.get('body') or ''}\n\n## Diff\n\n{diff}"
        )
    meta = json.loads(_gh_api(f"repos/{repo}/issues/{number}"))
    return (
        f"Issue #{number}: {meta.get('title', '')}\n"
        f"state: {meta.get('state')} | author: {meta.get('user', {}).get('login')}\n\n"
        f"{meta.get('body') or ''}"
    )


def _skills_root() -> Path:
    return Path(__file__).resolve().parent.parent / "oag_skills"


def fetch_skill(name: str, root: Optional[Path] = None) -> str:
    """Read a built-in skill's SKILL.md by name via the directory scan."""
    base = (root or _skills_root()) / name
    skill_file = base / "SKILL.md"
    if skill_file.is_file():
        return skill_file.read_text(encoding="utf-8")
    for category_dir in sorted((root or _skills_root()).iterdir()):
        candidate = category_dir / name / "SKILL.md"
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")
    raise SchemeError(f"no built-in skill named {name!r}")


def resolve(
    path: str,
    *,
    fetcher: Callable[[str, str, str], str] = fetch_github,
    skill_fetcher: Optional[Callable[[str], str]] = None,
    skills_root: Optional[Path] = None,
) -> str:
    """Resolve a scheme path to its text; non-scheme paths raise."""
    parsed = parse_scheme(path)
    if parsed is None:
        raise SchemeError(f"not a read-scheme path: {path!r}")
    if parsed["scheme"] == "skill":
        if skill_fetcher is not None:
            return skill_fetcher(parsed["name"])
        return fetch_skill(parsed["name"], root=skills_root)
    return fetcher(parsed["scheme"], parsed["repo"], parsed["number"])


def handles(path: str) -> bool:
    """True when resolve() would accept this path."""
    return _SCHEME_RE.match(path.strip()) is not None
