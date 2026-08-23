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

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


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


class HubUnavailable(Exception):
    """A hub source cannot be reached, e.g. the API rate limit is exhausted."""


class GitHubAuth:
    """Resolves a GitHub token: explicit arg, GITHUB_TOKEN, then gh CLI."""

    def __init__(self, token: Optional[str] = None) -> None:
        self._token = token
        self._gh_cli_token: Optional[str] = None
        self._gh_cli_checked = False

    def _gh_cli_token_lookup(self) -> Optional[str]:
        try:
            result = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if result.returncode != 0:
            return None
        return result.stdout.strip() or None

    def resolve_token(self) -> Optional[str]:
        if self._token:
            return self._token
        env_token = os.environ.get("GITHUB_TOKEN", "").strip()
        if env_token:
            return env_token
        if not self._gh_cli_checked:
            self._gh_cli_token = self._gh_cli_token_lookup()
            self._gh_cli_checked = True
        return self._gh_cli_token

    def auth_method(self) -> str:
        if self._token:
            return "token"
        if os.environ.get("GITHUB_TOKEN", "").strip():
            return "env"
        if self.resolve_token():
            return "gh-cli"
        return "none"

    def headers(self) -> dict[str, str]:
        headers = {"Accept": "application/vnd.github+json"}
        token = self.resolve_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers


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


def _description_score(description: str, query: str) -> float:
    desc = description.lower()
    tokens = [token for token in query.lower().split() if token]
    if not tokens:
        return 0.0
    unique = set(tokens)
    found = sum(1 for token in unique if token in desc)
    score = found / len(unique)
    if query.strip().lower() in desc:
        score += 0.5
    return score


class GitHubSource(_StubSource):
    name = "github"
    trust_level = "community"

    _API_BASE = "https://api.github.com"
    _TIMEOUT = 20

    def __init__(
        self,
        *_args: Any,
        auth: Any = None,
        token: Optional[str] = None,
        **_kwargs: Any,
    ) -> None:
        super().__init__(*_args, **_kwargs)
        self._auth = auth if isinstance(auth, GitHubAuth) else GitHubAuth(token=token)

    def _default_headers(self) -> dict[str, str]:
        return self._auth.headers()

    @staticmethod
    def _raise_if_rate_limited(exc: HTTPError, url: str) -> None:
        if exc.code == 403 and exc.headers.get("X-RateLimit-Remaining") == "0":
            raise HubUnavailable(f"GitHub API rate limit exhausted: {url}") from exc

    def _http_json(self, url: str, params: Optional[Mapping[str, Any]] = None) -> Any:
        query = urlencode(params) if params else ""
        full_url = f"{url}?{query}" if query else url
        request = Request(full_url, headers=self._default_headers())
        try:
            with urlopen(request, timeout=self._TIMEOUT) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            self._raise_if_rate_limited(exc, url)
            raise

    def _http_bytes(self, url: str) -> bytes:
        request = Request(url, headers=self._default_headers())
        try:
            with urlopen(request, timeout=self._TIMEOUT) as response:
                return response.read()
        except HTTPError as exc:
            self._raise_if_rate_limited(exc, url)
            raise

    @staticmethod
    def _split_identifier(identifier: str) -> Optional[tuple[str, str]]:
        parts = identifier.strip().strip("/").split("/")
        if len(parts) < 2 or not parts[0] or not parts[1]:
            return None
        return parts[0], parts[1]

    def search(self, query: str, *, limit: int = 50) -> list[SkillMeta]:
        payload = self._http_json(
            f"{self._API_BASE}/search/repositories",
            {
                "q": f"{query} SKILL.md in:path,readme",
                "sort": "stars",
                "per_page": max(1, min(int(limit), 50)),
            },
        )
        items = payload.get("items", []) if isinstance(payload, dict) else []
        scored: list[tuple[float, int, SkillMeta]] = []
        for item in items:
            owner = (item.get("owner") or {}).get("login", "")
            repo_name = item.get("name", "")
            identifier = f"{owner}/{repo_name}"
            description = item.get("description") or ""
            extra: dict[str, Any] = {"stars": item.get("stargazers_count", 0)}
            if item.get("pushed_at"):
                extra["pushed_at"] = item["pushed_at"]
            meta = SkillMeta(
                name=repo_name,
                description=description,
                source=self.name,
                identifier=identifier,
                trust_level=self.trust_level_for(identifier),
                repo=identifier,
                extra=extra,
            )
            stars = item.get("stargazers_count", 0)
            scored.append((_description_score(description, query), stars, meta))
        scored.sort(key=lambda entry: (-entry[0], -entry[1]))
        return [meta for _score, _stars, meta in scored]

    def inspect(self, identifier: str) -> Optional[SkillMeta]:
        split = self._split_identifier(identifier)
        if split is None:
            return None
        owner, repo = split
        try:
            payload = self._http_json(f"{self._API_BASE}/repos/{owner}/{repo}")
        except HTTPError as exc:
            if exc.code == 404:
                return None
            raise
        extra: dict[str, Any] = {"stars": payload.get("stargazers_count", 0)}
        default_branch = payload.get("default_branch")
        if default_branch:
            extra["default_branch"] = default_branch
        if payload.get("pushed_at"):
            extra["pushed_at"] = payload["pushed_at"]
        repo_id = f"{owner}/{repo}"
        return SkillMeta(
            name=payload.get("name", repo),
            description=payload.get("description") or "",
            source=self.name,
            identifier=repo_id,
            trust_level=self.trust_level_for(repo_id),
            repo=repo_id,
            extra=extra,
        )

    def fetch(self, identifier: str) -> Optional[bytes]:
        meta = self.inspect(identifier)
        if meta is None:
            return None
        split = self._split_identifier(identifier)
        if split is None:
            return None
        owner, repo = split
        branch = str(meta.extra.get("default_branch") or "main")
        url = (
            f"https://codeload.github.com/{owner}/{repo}"
            f"/tar.gz/refs/heads/{branch}"
        )
        try:
            return self._http_bytes(url)
        except HTTPError as exc:
            if exc.code == 404:
                return None
            raise

    def trust_level_for(self, identifier: str) -> str:
        return "community"


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
    "HubUnavailable",
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
