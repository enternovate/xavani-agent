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
import tempfile
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
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

    def source_id(self) -> str:
        return "skills-sh" if self.name == "skills.sh" else self.name

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


class _HttpApiSource(_StubSource):
    """Shared urllib plumbing: network only via these private methods."""

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


class GitHubSource(_HttpApiSource):
    name = "github"
    trust_level = "community"

    _API_BASE = "https://api.github.com"

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


class SkillsShSource(_HttpApiSource):
    name = "skills.sh"
    trust_level = "community"

    _SEARCH_URL = "https://www.skills.sh/api/search"
    _PREFIX = "skills-sh"
    _PREFIX_TYPOS = ("skils-sh",)

    def __init__(
        self,
        *_args: Any,
        github: Optional[GitHubSource] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*_args, **kwargs)
        self._github = github or GitHubSource(auth=self._auth)

    @classmethod
    def _strip_prefix(cls, identifier: str) -> str:
        text = identifier.strip().strip("/")
        for prefix in (cls._PREFIX, *cls._PREFIX_TYPOS):
            if text.startswith(f"{prefix}/"):
                return text[len(prefix) + 1:]
        return text

    @staticmethod
    def _name_score(name: str, query: str) -> float:
        tokens = {token for token in query.lower().split() if token}
        if not tokens:
            return 0.0
        haystack = name.lower()
        return sum(1 for token in tokens if token in haystack) / len(tokens)

    def search(self, query: str, *, limit: int = 50) -> list[SkillMeta]:
        payload = self._http_json(self._SEARCH_URL, {"q": query, "limit": int(limit)})
        entries = payload.get("skills") if isinstance(payload, dict) else None
        if not isinstance(entries, list):
            return []
        scored: list[tuple[float, int, SkillMeta]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            skill_id = str(entry.get("skillId") or entry.get("name") or "")
            repo = str(entry.get("source") or "")
            raw_id = str(entry.get("id") or "") or f"{repo}/{skill_id}".strip("/")
            installs = entry.get("installs", 0)
            meta = SkillMeta(
                name=skill_id,
                description=f"Skill {skill_id} listed on skills.sh",
                source=self.name,
                identifier=f"{self._PREFIX}/{raw_id}",
                trust_level=self.trust_level,
                repo=repo or None,
                path=skill_id or None,
                extra={"installs": installs},
            )
            scored.append((self._name_score(skill_id, query), int(installs or 0), meta))
        scored.sort(key=lambda item: (-item[0], -item[1]))
        return [meta for _score, _installs, meta in scored]

    def inspect(self, identifier: str) -> Optional[SkillMeta]:
        rest = self._strip_prefix(identifier)
        parts = [part for part in rest.split("/") if part]
        if len(parts) < 2:
            return None
        return self._github.inspect("/".join(parts[:2]))

    def fetch(self, identifier: str) -> Optional[bytes]:
        rest = self._strip_prefix(identifier)
        parts = [part for part in rest.split("/") if part]
        if len(parts) < 2:
            return None
        return self._github.fetch("/".join(parts[:2]))


class OptionalSkillSource(_StubSource):
    name = "official"
    trust_level = "official"

    _MANIFEST_PATH = (
        Path(__file__).resolve().parent.parent / "oag_skills" / "MANIFEST.json"
    )

    def __init__(self, *_args: Any, manifest_path: Any = None, **_kwargs: Any) -> None:
        super().__init__(*_args, **_kwargs)
        self._manifest_path = Path(manifest_path) if manifest_path else self._MANIFEST_PATH
        self._index: Optional[list[dict[str, Any]]] = None

    def _load_index(self) -> list[dict[str, Any]]:
        if self._index is None:
            try:
                payload = json.loads(
                    self._manifest_path.read_text(encoding="utf-8")
                )
            except (OSError, ValueError):
                payload = {}
            skills = payload.get("skills") if isinstance(payload, dict) else None
            self._index = [
                skill for skill in skills if isinstance(skill, dict)
            ] if isinstance(skills, list) else []
        return self._index

    @staticmethod
    def _meta_for(skill: dict[str, Any]) -> SkillMeta:
        name = str(skill.get("name") or "")
        return SkillMeta(
            name=name,
            description=str(skill.get("description") or ""),
            source=OptionalSkillSource.name,
            identifier=name,
            trust_level=OptionalSkillSource.trust_level,
        )

    def search(self, query: str, *, limit: int = 50) -> list[SkillMeta]:
        tokens = {token for token in query.lower().split() if token}
        scored: list[tuple[float, SkillMeta]] = []
        for skill in self._load_index():
            meta = self._meta_for(skill)
            if tokens:
                haystack = f"{meta.name} {meta.description}".lower()
                score = sum(1 for token in tokens if token in haystack) / len(tokens)
                if score <= 0:
                    continue
            else:
                score = 0.0
            scored.append((score, meta))
        scored.sort(key=lambda item: -item[0])
        try:
            cap = max(0, int(limit))
        except (TypeError, ValueError):
            cap = 50
        return [meta for _score, meta in scored[:cap]]

    def inspect(self, identifier: str) -> Optional[SkillMeta]:
        for skill in self._load_index():
            if str(skill.get("name") or "") == identifier:
                return self._meta_for(skill)
        return None

    def fetch(self, _identifier: str) -> Optional[bytes]:
        return None

    def trust_level_for(self, _identifier: str) -> str:
        return self.trust_level


class WellKnownSkillSource(_HttpApiSource):
    name = "well-known"
    trust_level = "official"

    @staticmethod
    def _split_identifier(identifier: str) -> tuple[str, str]:
        text = identifier.strip()
        if text.startswith(("http://", "https://")):
            parsed = urlsplit(text)
            host = parsed.netloc
            skill = parsed.path.strip("/")
        else:
            parts = [part for part in text.split("/") if part]
            host = parts[0] if parts else ""
            skill = "/".join(parts[1:])
        return host, skill

    def search(self, _query: str, *, limit: int = 50) -> list[SkillMeta]:
        return []

    def _find_entry(
        self, identifier: str
    ) -> tuple[Optional[dict[str, Any]], str]:
        host, skill = self._split_identifier(identifier)
        manifest_url = f"https://{host}/.well-known/agent-skills.json"
        if not host:
            return None, manifest_url
        try:
            payload = self._http_json(manifest_url)
        except HTTPError as exc:
            if exc.code == 404:
                return None, manifest_url
            raise
        entries = payload.get("skills") if isinstance(payload, dict) else None
        if not isinstance(entries, list):
            return None, manifest_url
        named = [entry for entry in entries if isinstance(entry, dict)]
        if skill:
            match = next(
                (entry for entry in named if entry.get("name") == skill), None
            )
        else:
            match = named[0] if len(named) == 1 else None
        return match, manifest_url

    def inspect(self, identifier: str) -> Optional[SkillMeta]:
        host, _skill = self._split_identifier(identifier)
        entry, manifest_url = self._find_entry(identifier)
        if entry is None:
            return None
        name = str(entry.get("name") or "")
        return SkillMeta(
            name=name,
            description=str(entry.get("description") or ""),
            source=self.name,
            identifier=f"{host}/{name}",
            trust_level="official",
            extra={"manifest_url": manifest_url},
        )

    def fetch(self, identifier: str) -> Optional[bytes]:
        host, _skill = self._split_identifier(identifier)
        entry, _manifest_url = self._find_entry(identifier)
        if entry is None:
            return None
        target = entry.get("url")
        if not target:
            return None
        target = str(target)
        if target.startswith("/"):
            target = f"https://{host}{target}"
        try:
            return self._http_bytes(target)
        except HTTPError as exc:
            if exc.code == 404:
                return None
            raise

    def trust_level_for(self, _identifier: str) -> str:
        return self.trust_level


class ClawHubSource(_HttpApiSource):
    name = "clawhub"
    trust_level = "community"

    _SEARCH_URL = "https://clawhub.ai/api/search"

    def search(self, query: str, *, limit: int = 50) -> list[SkillMeta]:
        payload = self._http_json(self._SEARCH_URL, {"q": query, "limit": int(limit)})
        entries = payload.get("results") if isinstance(payload, dict) else None
        if not isinstance(entries, list):
            return []
        tokens = {token for token in query.lower().split() if token}
        scored: list[tuple[float, int, SkillMeta]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            install = entry.get("install") or {}
            reference = str(install.get("reference") or "") or str(
                entry.get("canonicalUrl") or ""
            ).strip("/")
            if not reference:
                continue
            skill = entry.get("skill") or {}
            stats = skill.get("stats") or {}
            display_name = str(entry.get("displayName") or reference)
            summary = str(skill.get("summary") or "")
            downloads = stats.get("downloads", entry.get("downloads", 0)) or 0
            meta = SkillMeta(
                name=display_name,
                description=summary,
                source=self.name,
                identifier=reference,
                trust_level=self.trust_level,
                extra={
                    "downloads": downloads,
                    "installs": stats.get("installs", 0),
                    "stars": stats.get("stars", 0),
                },
            )
            haystack = f"{display_name} {summary}".lower()
            score = (
                sum(1 for token in tokens if token in haystack) / len(tokens)
                if tokens
                else 0.0
            )
            scored.append((score, int(downloads), meta))
        scored.sort(key=lambda item: (-item[0], -item[1]))
        return [meta for _score, _downloads, meta in scored]

    def inspect(self, identifier: str) -> Optional[SkillMeta]:
        for meta in self.search(identifier):
            if meta.identifier == identifier:
                return meta
        return None

    def fetch(self, _identifier: str) -> Optional[bytes]:
        return None


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
    """Tap registry persisted as JSON at ``TAPS_FILE`` (atomic, mode 0600)."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path is not None else TAPS_FILE

    def _load(self) -> list[dict[str, Any]]:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        taps = payload.get("taps") if isinstance(payload, dict) else None
        if not isinstance(taps, list):
            return []
        return [tap for tap in taps if isinstance(tap, dict)]

    def _save(self, taps: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.", dir=str(self.path.parent)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump({"taps": taps}, handle, indent=2)
                handle.write("\n")
            os.chmod(tmp_name, 0o600)
            os.replace(tmp_name, self.path)
        except BaseException:
            with suppress(OSError):
                os.unlink(tmp_name)
            raise

    def list_taps(self) -> list[dict[str, str]]:
        return [dict(tap) for tap in self._load()]

    def add_tap(self, name: str, repo: str) -> bool:
        taps = self._load()
        if any(tap.get("name") == name for tap in taps):
            return False
        taps.append(
            {
                "name": name,
                "repo": repo,
                "added": datetime.now(timezone.utc).isoformat(),
            }
        )
        self._save(taps)
        return True

    def remove_tap(self, name: str) -> bool:
        taps = self._load()
        kept = [tap for tap in taps if tap.get("name") != name]
        if len(kept) == len(taps):
            return False
        self._save(kept)
        return True


_SOURCE_ID_ATTR = "source_id"


def _source_id_of(src: Any) -> str:
    getter = getattr(src, _SOURCE_ID_ATTR, None)
    if callable(getter):
        return str(getter())
    return str(getattr(src, "name", ""))


def create_source_router(*args: Any, **kwargs: Any) -> list[Any]:
    """Return source instances in search priority order (upstream contract)."""
    auth = args[0] if args else kwargs.get("auth")
    github = GitHubSource(auth=auth, token=kwargs.get("token"))
    return [
        OptionalSkillSource(),
        SkillsShSource(auth=auth, github=github),
        WellKnownSkillSource(auth=auth),
        UrlSource(),
        github,
        ClawHubSource(auth=auth),
    ]


def parallel_search_sources(
    sources: list[Any],
    query: str = "",
    per_source_limits: Optional[Mapping[str, int]] = None,
    source_filter: str = "all",
    overall_timeout: float = 30,
    on_source_done: Optional[Any] = None,
) -> tuple[list[SkillMeta], dict[str, int], list[str]]:
    from concurrent.futures import ThreadPoolExecutor, as_completed

    per_source_limits = dict(per_source_limits or {})
    active = [
        src
        for src in sources
        if source_filter == "all"
        or _source_id_of(src) == source_filter
        or _source_id_of(src) == "official"
    ]
    all_results: list[SkillMeta] = []
    source_counts: dict[str, int] = {}
    timed_out_ids: list[str] = []
    if not active:
        return all_results, source_counts, timed_out_ids

    def _one(src: Any) -> tuple[str, list[SkillMeta]]:
        try:
            sid = _source_id_of(src)
            lim = per_source_limits.get(sid, 50)
            return sid, list(src.search(query, limit=lim))
        except Exception:
            return _source_id_of(src), []

    with ThreadPoolExecutor(max_workers=min(len(active), 8)) as pool:
        futures = {pool.submit(_one, src): src for src in active}
        try:
            for fut in as_completed(futures, timeout=overall_timeout):
                try:
                    sid, results = fut.result(timeout=0)
                    source_counts[sid] = len(results)
                    all_results.extend(results)
                    if on_source_done:
                        on_source_done(sid, len(results))
                except Exception:
                    pass
        except TimeoutError:
            timed_out_ids = [
                _source_id_of(futures[fut]) for fut in futures if not fut.done()
            ]

    return all_results, source_counts, timed_out_ids


_TRUST_RANK = {"builtin": 3, "trusted": 2, "community": 1}


def unified_search(
    query: str,
    sources: list[Any],
    source_filter: str = "all",
    limit: int = 10,
) -> list[SkillMeta]:
    all_results, _, _ = parallel_search_sources(
        sources,
        query=query,
        source_filter=source_filter,
        overall_timeout=30,
    )
    seen: dict[str, SkillMeta] = {}
    for r in all_results:
        if r.name not in seen:
            seen[r.name] = r
        elif _TRUST_RANK.get(r.trust_level, 0) > _TRUST_RANK.get(
            seen[r.name].trust_level, 0
        ):
            seen[r.name] = r
    deduped = sorted(
        seen.values(),
        key=lambda m: -_TRUST_RANK.get(m.trust_level, 0),
    )
    return deduped[:limit]


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
