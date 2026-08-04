# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""G08: pre-computed context prefetch.

Before the user asks, gather cheap, high-signal context so the agent
starts a session informed:

- git state when the session starts inside a repository (branch,
  status summary, recent commits)
- durable facts from past sessions (B02 confidence-filtered recall)
- pattern instincts from the tool-chain registry (B01)

Everything is best-effort and bounded: each probe has a timeout, and a
failure never blocks session startup. The prefetch runs on explicit
hooks (session start) — no speculative subscriptions.
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_GIT_TIMEOUT = 5


def _run_git(args: List[str], cwd: Optional[str] = None) -> Optional[str]:
    """Run a git command; return stdout or None on any failure."""
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True, text=True, timeout=_GIT_TIMEOUT,
            cwd=cwd,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def git_repo_root(cwd: Optional[str] = None) -> Optional[str]:
    """Return the git repo root for cwd, or None."""
    root = _run_git(["rev-parse", "--show-toplevel"], cwd=cwd)
    return root if root else None


def prefetch_git_state(cwd: Optional[str] = None) -> Dict[str, Any]:
    """Gather git state when inside a repository. Empty dict outside."""
    root = git_repo_root(cwd)
    if not root:
        return {}
    state: Dict[str, Any] = {"repo_root": root}
    branch = _run_git(["branch", "--show-current"], cwd=root)
    if branch:
        state["branch"] = branch
    status = _run_git(["status", "--short"], cwd=root)
    if status:
        lines = [ln.strip() for ln in status.splitlines() if ln.strip()]
        state["changed_files"] = len(lines)
        state["status_preview"] = "\n".join(lines[:10])
    log = _run_git(["log", "--oneline", "-5"], cwd=root)
    if log:
        state["recent_commits"] = log.splitlines()
    return state


def prefetch_session_facts(session_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Recall confidence-filtered durable facts (B02)."""
    try:
        from xavani_memory.summarizer import recall_facts

        return recall_facts(session_id=session_id, limit=10)
    except Exception:
        return []


def prefetch_instincts(tool_names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Match stored tool-chain patterns (B01)."""
    if not tool_names or len(tool_names) < 2:
        return []
    try:
        from xavani_memory.instincts import InstinctRegistry

        return InstinctRegistry().match(tool_names, limit=3)
    except Exception:
        return []


def build_prefetch_context(
    cwd: Optional[str] = None,
    session_id: Optional[str] = None,
    tool_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Compose the full prefetch context block (G08).

    Returns a dict with ``git``, ``durable_facts``, and ``instincts``
    keys. Callers format it into the system prompt at session start.
    """
    return {
        "git": prefetch_git_state(cwd),
        "durable_facts": prefetch_session_facts(session_id),
        "instincts": prefetch_instincts(tool_names),
    }


def format_prefetch_block(context: Dict[str, Any]) -> str:
    """Render the prefetch context as a compact prompt block."""
    lines: List[str] = []
    git = context.get("git") or {}
    if git:
        lines.append("Repository context (prefetched):")
        if git.get("branch"):
            lines.append(f"- branch: {git['branch']}")
        if git.get("changed_files"):
            lines.append(f"- {git['changed_files']} changed file(s)")
            preview = git.get("status_preview")
            if preview:
                lines.append(f"  status:\n{preview}")
        if git.get("recent_commits"):
            lines.append("- recent commits:")
            for commit in git["recent_commits"]:
                lines.append(f"  {commit}")
    facts = context.get("durable_facts") or []
    if facts:
        lines.append("Durable facts from past sessions:")
        for fact in facts[:5]:
            lines.append(f"- [{fact.get('confidence', 0):.0%}] {fact.get('fact', '')}")
    instincts = context.get("instincts") or []
    if instincts:
        lines.append("Pattern instincts (verify before trusting):")
        for inst in instincts[:3]:
            lines.append(
                f"- '{inst.get('pattern')}' x{inst.get('count', 0)}"
            )
    if not lines:
        return ""
    return "\n".join([""] + lines + [""])


def _is_within_repo(cwd: str) -> bool:
    """Cheap guard: does cwd sit under a .git directory?"""
    try:
        path = Path(cwd).resolve()
        for parent in [path, *path.parents]:
            if (parent / ".git").exists():
                return True
    except OSError:
        pass
    return False


def prefetch_enabled() -> bool:
    """True when prefetch is enabled (default)."""
    return os.environ.get("XAVANI_DISABLE_PREFETCH") != "1"
