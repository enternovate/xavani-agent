# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Deterministic perception collectors (v0.7.0 operator U9–U14).

"Perceive" is the first step of the operator loop: gather the product's current
state so the deterministic opportunity rules have something to react to. Every
collector here is **pure, read-only, and makes no LLM call** (R10) — it shells
out to ``git``, scans the tree, or reads cheap cached signals (e.g. pytest's own
``lastfailed`` cache). The operator never runs the test suite *during* perceive;
it reads the last known result (the suite is run by ``verify`` in M3).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Callable

from xavani_operator.types import Perception

_IGNORE_DIRS = {
    ".git", ".pytest_cache", ".ruff_cache", "__pycache__", "node_modules",
    ".venv", "venv", "dist", "build", ".mypy_cache", ".xavani", ".idea", ".tox",
    ".next", ".turbo", "coverage", ".cache",
}
_TEXT_EXTS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".rb", ".c",
    ".cpp", ".h", ".hpp", ".cs", ".php", ".swift", ".kt", ".md", ".txt", ".rst",
    ".yaml", ".yml", ".toml", ".cfg", ".ini", ".sh", ".sql", ".html", ".css", ".vue",
}
_MARKER_RE = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b")


def _git(repo: str, *args: str) -> tuple[int, str]:
    """Run a read-only git command; return (returncode, stdout)."""
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=15,
        )
        return proc.returncode, proc.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return 1, ""


def collect_repo_signals(repo_path: str | Path) -> dict:
    """Git state of ``repo_path``: branch, dirtiness, recent commit subjects."""
    repo = str(repo_path)
    code, _ = _git(repo, "rev-parse", "--is-inside-work-tree")
    if code != 0:
        return {"is_git": False, "branch": "", "dirty": False, "dirty_files": 0, "recent_commits": []}
    _, branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    _, status = _git(repo, "status", "--porcelain")
    dirty_files = len([ln for ln in status.splitlines() if ln.strip()])
    _, log = _git(repo, "log", "-5", "--pretty=%s")
    recent = [ln for ln in log.splitlines() if ln.strip()]
    return {
        "is_git": True,
        "branch": branch,
        "dirty": dirty_files > 0,
        "dirty_files": dirty_files,
        "recent_commits": recent,
    }


def collect_test_signals(repo_path: str | Path) -> dict:
    """Last-known test health from pytest's ``lastfailed`` cache (no run)."""
    lastfailed = Path(repo_path) / ".pytest_cache" / "v" / "cache" / "lastfailed"
    if lastfailed.exists():
        try:
            data = json.loads(lastfailed.read_text(encoding="utf-8"))
            return {"known": True, "failing": len(data), "source": "pytest_cache"}
        except (OSError, json.JSONDecodeError):
            pass
    return {"known": False, "failing": 0}


def collect_issue_signals(repo_path: str | Path, max_results: int = 200) -> list[dict]:
    """Scan source files for TODO/FIXME/XXX/HACK markers (deterministic order)."""
    root = Path(repo_path)
    out: list[dict] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _IGNORE_DIRS]
        for fn in filenames:
            if Path(fn).suffix.lower() not in _TEXT_EXTS:
                continue
            fpath = Path(dirpath) / fn
            try:
                text = fpath.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for lineno, line in enumerate(text.splitlines(), start=1):
                match = _MARKER_RE.search(line)
                if match:
                    out.append({
                        "file": str(fpath.relative_to(root)),
                        "line": lineno,
                        "marker": match.group(1),
                        "text": line.strip()[:200],
                    })
    out.sort(key=lambda d: (d["file"], d["line"]))
    return out[:max_results]


def collect_channel_signals(
    channels,
    inbox_provider: Callable[[str, str], Any] | None = None,
) -> dict:
    """Project configured channels into a signal map.

    Perceive stays offline by default (no network per R10): ``unread`` is ``None``
    unless an ``inbox_provider(platform, handle) -> count`` is supplied (the
    promote workstream wires a real one in M5).
    """
    out: dict[str, dict] = {}
    for ch in channels:
        platform = ch["platform"] if isinstance(ch, dict) else ch.platform
        handle = (ch.get("handle", "") if isinstance(ch, dict) else ch.handle) or ""
        unread = inbox_provider(platform, handle) if inbox_provider is not None else None
        out[platform] = {"handle": handle, "unread": unread}
    return out


def collect_last_cycle(state) -> dict | None:
    """The most recent persisted ``CycleReport`` dict from state, or ``None``."""
    cycles = state.list("cycles") if state is not None else []
    if not cycles:
        return None
    return max(cycles, key=lambda c: c.get("created_at", 0))


def collect_metrics_signals(metrics_path: str | Path | None = None) -> dict:
    """Read a product metrics JSON file if present; else empty (deterministic)."""
    if metrics_path is None:
        return {}
    p = Path(metrics_path)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def perception_hash(perception: Perception) -> str:
    """Stable 16-char digest of a Perception's signal sections (not timestamps)."""
    payload = json.dumps(
        {
            "repo": perception.repo,
            "tests": perception.tests,
            "issues": perception.issues,
            "channels": perception.channels,
            "metrics": perception.metrics,
            "last_cycle": perception.last_cycle,
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def perception_changed(perception: Perception, last_hash: str | None) -> bool:
    """True if this perception differs from the last seen content hash."""
    return last_hash != perception.content_hash


def perceive(config, state=None, inbox_provider=None, metrics_path=None) -> Perception:
    """Assemble a full :class:`Perception` from the deterministic collectors."""
    repo_path = config.product.repo or "."
    perception = Perception(
        repo=collect_repo_signals(repo_path),
        tests=collect_test_signals(repo_path),
        issues=collect_issue_signals(repo_path),
        channels=collect_channel_signals(config.channels, inbox_provider),
        metrics=collect_metrics_signals(metrics_path),
        last_cycle=collect_last_cycle(state),
    )
    perception.content_hash = perception_hash(perception)
    return perception
