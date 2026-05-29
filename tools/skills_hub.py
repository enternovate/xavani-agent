# MIT License
#
# Copyright (c) 2025-2026 Enternovate
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# ============================================================================
# Xavani Agent — Skills Hub source registry
# ============================================================================

"""Minimal stubs for the Skills Hub source registry.

The full implementation (GitHub crawler, taps, audit log, lockfile) was
stripped from this fork. This module keeps the public import contract stable
so that:

* `xavani_cli.skills_hub` can still import lazily without crashing.
* `scripts/build_skills_index.py` runs and emits an empty index when the hub
  is unavailable (it checks for `_SKILLS_HUB_AVAILABLE` itself).
* The test suite collects without import errors. Tests that exercise the
  removed functionality are skipped at the file level via `pytestmark`.

All sources return empty results and all actions are no-ops, so `xavani skills`
gracefully reports "no entries found" instead of crashing.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional


XAVANI_HOME = Path(os.environ.get("XAVANI_HOME") or Path.home() / ".xavani")
_HOME = XAVANI_HOME  # backward-compat alias for older internal callers
SKILLS_DIR: Path = XAVANI_HOME / "skills"
HUB_DIR: Path = SKILLS_DIR / ".hub"
LOCK_FILE: Path = HUB_DIR / "lock.json"
QUARANTINE_DIR: Path = HUB_DIR / "quarantine"
AUDIT_LOG: Path = HUB_DIR / "audit.log"
TAPS_FILE: Path = HUB_DIR / "taps.json"
INDEX_CACHE_DIR: Path = HUB_DIR / "index-cache"


@dataclass
class SkillMeta:
    """Lightweight description of a discoverable skill."""

    name: str = ""
    description: str = ""
    source: str = ""
    identifier: str = ""
    trust_level: str = "unknown"
    repo: Optional[str] = None
    path: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


class GitHubAuth:
    """Stub: reports no authentication available."""

    def __init__(self, token: Optional[str] = None) -> None:
        self._token = token

    def auth_method(self) -> str:
        return "anonymous"

    def headers(self) -> dict[str, str]:
        return {}


class _StubSource:
    """Base class for every source — returns no results."""

    name: str = "stub"
    trust_level: str = "unknown"

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        pass

    def search(self, _query: str, *, limit: int = 50) -> list[SkillMeta]:
        return []

    def inspect(self, _identifier: str) -> Optional[SkillMeta]:
        return None

    def fetch(self, _identifier: str) -> Optional[bytes]:
        return None

    def trust_level_for(self, _identifier: str) -> str:
        return self.trust_level

    @staticmethod
    def _parse_frontmatter_quick(_content: str) -> dict[str, Any]:
        return {}


class GitHubSource(_StubSource):
    name = "github"


class SkillsShSource(_StubSource):
    name = "skills.sh"


class OptionalSkillSource(_StubSource):
    name = "official"


class WellKnownSkillSource(_StubSource):
    name = "well-known"


class ClawHubSource(_StubSource):
    name = "clawhub"


class ClaudeMarketplaceSource(_StubSource):
    name = "claude-marketplace"


class LobeHubSource(_StubSource):
    name = "lobehub"


class UrlSource(_StubSource):
    name = "url"


@dataclass
class SkillBundle:
    """Bundle of files that make up a single skill."""

    identifier: str = ""
    source: str = ""
    files: dict[str, bytes] = field(default_factory=dict)
    meta: Optional[SkillMeta] = None


def bundle_content_hash(_bundle: SkillBundle) -> str:
    return "0" * 64


def _skill_meta_to_dict(meta: SkillMeta) -> dict[str, Any]:
    return {
        "name": meta.name,
        "description": meta.description,
        "source": meta.source,
        "identifier": meta.identifier,
        "trust_level": meta.trust_level,
        "repo": meta.repo or "",
        "path": meta.path or "",
        "tags": list(meta.tags or ()),
        "extra": dict(meta.extra or {}),
    }


def quarantine_bundle(*_args: Any, **_kwargs: Any) -> Optional[Path]:
    return None


class HubLockFile:
    """Stub lockfile that reports an empty install set."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or (SKILLS_DIR / ".hub" / "lock.json")

    def load(self) -> dict[str, Any]:
        return {}

    def save(self, _data: Mapping[str, Any]) -> None:
        return None

    def list_skills(self) -> list[dict[str, Any]]:
        return []

    def list_installed(self) -> list[dict[str, Any]]:
        return []


class TapsManager:
    """Stub tap registry."""

    def __init__(self) -> None:
        self._taps: dict[str, str] = {}

    def list_taps(self) -> list[dict[str, str]]:
        return []

    def add_tap(self, _name: str, _repo: str) -> None:
        return None

    def remove_tap(self, _name: str) -> None:
        return None


def create_source_router(*_args: Any, **_kwargs: Any) -> dict[str, _StubSource]:
    return {
        "github": GitHubSource(),
        "skills.sh": SkillsShSource(),
        "official": OptionalSkillSource(),
        "well-known": WellKnownSkillSource(),
        "clawhub": ClawHubSource(),
        "claude-marketplace": ClaudeMarketplaceSource(),
        "lobehub": LobeHubSource(),
    }


def unified_search(_query: str, *_args: Any, **_kwargs: Any) -> list[SkillMeta]:
    return []


def append_audit_log(*_args: Any, **_kwargs: Any) -> None:
    return None


def ensure_hub_dirs() -> Path:
    import json as _json
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    hub = SKILLS_DIR / ".hub"
    hub.mkdir(parents=True, exist_ok=True)
    lock = hub / "lock.json"
    if not lock.exists():
        lock.write_text(_json.dumps({}), encoding="utf-8")
    (hub / "quarantine").mkdir(exist_ok=True)
    (hub / "index-cache").mkdir(exist_ok=True)
    return SKILLS_DIR


def check_for_skill_updates(*_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
    return []


def uninstall_skill(_name: str, *_args: Any, **_kwargs: Any) -> bool:
    return False


def install_from_quarantine(*_args: Any, **_kwargs: Any) -> bool:
    """Stub — quarantine flow stripped along with the rest of the hub."""
    return False


def _write_index_cache(key: str, data: Any, **_kwargs: Any) -> None:
    """Write index cache entry and create .ignore file in HUB_DIR."""
    import json as _json
    try:
        INDEX_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = INDEX_CACHE_DIR / f"{key}.json"
        cache_file.write_text(_json.dumps(data), encoding="utf-8")
        ignore_file = HUB_DIR / ".ignore"
        if not ignore_file.exists():
            HUB_DIR.mkdir(parents=True, exist_ok=True)
            ignore_file.write_text("*\n", encoding="utf-8")
    except OSError:
        pass


def _read_index_cache(*_args: Any, **_kwargs: Any) -> Optional[Any]:
    """Internal helper kept for tests that mock it."""
    return None


__all__ = [
    "GitHubAuth",
    "GitHubSource",
    "SkillsShSource",
    "OptionalSkillSource",
    "WellKnownSkillSource",
    "ClawHubSource",
    "ClaudeMarketplaceSource",
    "LobeHubSource",
    "UrlSource",
    "SkillMeta",
    "SkillBundle",
    "HubLockFile",
    "TapsManager",
    "SKILLS_DIR",
    "HUB_DIR",
    "LOCK_FILE",
    "QUARANTINE_DIR",
    "AUDIT_LOG",
    "TAPS_FILE",
    "INDEX_CACHE_DIR",
    "XAVANI_HOME",
    "create_source_router",
    "unified_search",
    "append_audit_log",
    "ensure_hub_dirs",
    "check_for_skill_updates",
    "uninstall_skill",
    "install_from_quarantine",
    "bundle_content_hash",
    "quarantine_bundle",
]
