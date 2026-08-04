"""D08: dependency provenance report (``xavani deps-provenance``).

Lists every direct dependency with its resolved source (PyPI registry or
git fork), version, and first lockfile hash — plus the last audit date
(the last commit date touching pyproject.toml or uv.lock). Output is a
plain-text table by default, JSON with ``--json``.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _git_date(path: Path) -> str:
    """Last commit date touching ``path`` (``YYYY-MM-DD``), or empty."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", str(path)],
            cwd=str(_REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return (result.stdout or "").strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return ""


def _direct_dependencies() -> List[str]:
    """Extract direct dependency specifiers from the [project] dependencies block."""
    text = (_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    block_match = re.search(r"\[project\]\n(.*?)(?:\n\[|\Z)", text, re.S)
    if not block_match:
        return []
    deps_match = re.search(
        r"dependencies = \[(.*?)^\]", block_match.group(1), re.S | re.M
    )
    if not deps_match:
        return []
    names: List[str] = []
    for line in deps_match.group(1).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        stripped = stripped.strip('",')
        if stripped:
            names.append(stripped)
    return names


def _lock_entry(name: str) -> Dict[str, Any]:
    """Find ``name`` in uv.lock; return source/version/hash info."""
    name = name.lower()
    # uv.lock normalizes names per PEP 503 (dashes -> underscores).
    lock_name = name.replace("-", "_")
    lock = (_REPO_ROOT / "uv.lock").read_text(encoding="utf-8")
    # Find the package block: [[package]] name = "<name>"
    blocks = lock.split("[[package]]")
    for block in blocks[1:]:
        m = re.search(r'name = "([^"]+)"', block)
        if not m or m.group(1).lower() != lock_name:
            continue
        version = ""
        vm = re.search(r'version = "([^"]+)"', block)
        if vm:
            version = vm.group(1)
        source = "pypi"
        sm = re.search(r'source = \{ ([^}]+) \}', block)
        if sm and "registry" not in sm.group(1):
            source = sm.group(1).strip()
        hashes = re.findall(r"sha256:([0-9a-f]{64})", block)
        return {
            "name": name,
            "version": version,
            "source": source,
            "hash": hashes[0][:16] if hashes else "",
        }
    return {"name": name, "version": "", "source": "unknown", "hash": ""}


def build_provenance_report() -> List[Dict[str, Any]]:
    """Build the provenance rows for all direct dependencies."""
    audit_date = _git_date(_REPO_ROOT / "pyproject.toml") or _git_date(
        _REPO_ROOT / "uv.lock"
    )
    rows = []
    for spec in _direct_dependencies():
        name_match = re.match(r'["\']?([A-Za-z0-9_.-]+)', spec)
        if not name_match:
            continue
        name = name_match.group(1).lower()
        entry = _lock_entry(name)
        entry["specifier"] = spec.strip()
        entry["audit_date"] = audit_date
        rows.append(entry)
    rows.sort(key=lambda r: r["name"])
    return rows


def render_report(rows: List[Dict[str, Any]]) -> str:
    """Render the provenance rows as a terminal table."""
    lines = ["Dependency provenance", ""]
    header = f"{'name':<32} {'version':<14} {'source':<24} {'hash':<18} audit"
    lines.append(header)
    lines.append("-" * len(header))
    for r in rows:
        lines.append(
            f"{r['name']:<32} {r['version']:<14} {r['source']:<24} "
            f"{r['hash']:<18} {r['audit_date']}"
        )
    lines.append("")
    lines.append(
        "Source: uv.lock. Audit date = last commit touching pyproject.toml/uv.lock."
    )
    return "\n".join(lines)


def cmd_deps_provenance(args) -> int:
    """CLI entry point for ``xavani deps-provenance``."""
    rows = build_provenance_report()
    if getattr(args, "json", False):
        print(json.dumps(rows, indent=2, ensure_ascii=False))
    else:
        print(render_report(rows))
    return 0


__all__ = ["build_provenance_report", "render_report", "cmd_deps_provenance"]
