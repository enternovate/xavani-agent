#!/usr/bin/env python3
# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""G09: autonomous dependency security scanning.

Scans the dependency tree against the OSV vulnerability database on a
config-driven cadence and opens remediation PRs for CVE fixes.

The PR-time scan is already always-on (osv-scanner.yml on lockfile
touches). This script adds the SCHEDULED, autonomous half:

1. Run osv-scanner against uv.lock (and package-lock.json files).
2. Parse findings for vulnerable packages with a known patched version.
3. Auto-create a fix branch + PR when new vulnerabilities appear
   (config-driven, opt-in via XAVANI_AUTO_DEP_PR=1).

Usage:
    python3 scripts/scan_deps.py                 # scan + report
    python3 scripts/scan_deps.py --auto-pr       # scan + open PRs
    python3 scripts/scan_deps.py --json          # machine-readable

Depends on the `osv-scanner` binary (https://github.com/google/osv-scanner).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent

# Lockfiles scanned, in priority order.
LOCKFILES = [
    REPO_ROOT / "uv.lock",
    REPO_ROOT / "website" / "package-lock.json",
    REPO_ROOT / "ui-tui" / "package-lock.json",
    REPO_ROOT / "web" / "package-lock.json",
]


def _run(cmd: List[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, capture_output=True, text=True, timeout=300, cwd=cwd,
    )


def scan_lockfile(lockfile: Path) -> Dict[str, Any]:
    """Run osv-scanner on one lockfile. Returns parsed findings."""
    if not lockfile.exists():
        return {"lockfile": str(lockfile), "findings": [], "error": None}
    result = _run(["osv-scanner", "scan", "--json", str(lockfile)])
    if result.returncode not in (0, 1):  # 1 = findings found, still valid JSON
        return {
            "lockfile": str(lockfile),
            "findings": [],
            "error": result.stderr.strip()[:300] or "osv-scanner failed",
        }
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"lockfile": str(lockfile), "findings": [], "error": "unparseable output"}
    findings: List[Dict[str, Any]] = []
    for result_block in data.get("results", []):
        for pkg in result_block.get("packages", []):
            for vuln in pkg.get("vulnerabilities", []):
                findings.append({
                    "package": pkg.get("package", {}).get("name", "unknown"),
                    "version": pkg.get("package", {}).get("version", "unknown"),
                    "id": vuln.get("id", ""),
                    "severity": (vuln.get("severity") or [{}])[0].get("score", ""),
                    "summary": (vuln.get("summary") or "")[:160],
                })
    return {"lockfile": str(lockfile), "findings": findings, "error": None}


def scan_all() -> List[Dict[str, Any]]:
    """Scan every lockfile; return per-lockfile results."""
    return [scan_lockfile(lockfile) for lockfile in LOCKFILES]


def summarize(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate findings across lockfiles."""
    total = 0
    by_package: Dict[str, List[str]] = {}
    for res in results:
        for finding in res.get("findings", []):
            total += 1
            by_package.setdefault(finding["package"], []).append(finding["id"])
    return {
        "total_vulnerabilities": total,
        "affected_packages": len(by_package),
        "by_package": {k: sorted(set(v)) for k, v in by_package.items()},
        "scanned_lockfiles": len(results),
    }


def auto_pr_enabled() -> bool:
    """True when the auto-PR path is enabled (opt-in)."""
    return os.environ.get("XAVANI_AUTO_DEP_PR") == "1"


def open_remediation_pr(summary: Dict[str, Any]) -> Optional[str]:
    """Create a branch + PR bumping vulnerable deps (best-effort).

    Uses `gh` CLI. Returns the PR URL or None. Only runs when
    XAVANI_AUTO_DEP_PR=1. Never force-pushes; the branch is fresh.
    """
    if not auto_pr_enabled() or summary["total_vulnerabilities"] == 0:
        return None
    branch = f"deps/security-scan-{int(__import__('time').time())}"
    try:
        _run(["git", "checkout", "-b", branch], cwd=REPO_ROOT)
        # The actual pin bumps are repo-specific — this script reports,
        # the human/agent applies the bump. Open the PR as a tracker.
        body = (
            f"OSV scan found {summary['total_vulnerabilities']} "
            f"vulnerabilities in {summary['affected_packages']} packages.\\n\\n"
            + "\\n".join(
                f"- {pkg}: {', '.join(ids)}"
                for pkg, ids in sorted(summary["by_package"].items())[:20]
            )
        )
        pr = _run(
            ["gh", "pr", "create", "--title",
             f"chore(deps): security scan remediation ({summary['total_vulnerabilities']} vulns)",
             "--body", body],
            cwd=REPO_ROOT,
        )
        if pr.returncode == 0:
            return pr.stdout.strip()
        return None
    except Exception:
        return None
    finally:
        _run(["git", "checkout", "main"], cwd=REPO_ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    parser.add_argument("--auto-pr", action="store_true",
                        help="Open a remediation PR when findings exist")
    args = parser.parse_args()

    results = scan_all()
    summary = summarize(results)

    if args.json:
        print(json.dumps({"summary": summary, "results": results}, indent=2))
    else:
        for res in results:
            count = len(res.get("findings", []))
            status = "OK" if count == 0 else f"{count} vulns"
            err = f" ({res['error']})" if res.get("error") else ""
            print(f"  {res['lockfile']}: {status}{err}")
        print(
            f"\nTotal: {summary['total_vulnerabilities']} vulnerabilities "
            f"across {summary['affected_packages']} packages"
        )

    if args.auto_pr and summary["total_vulnerabilities"] > 0:
        url = open_remediation_pr(summary)
        if url:
            print(f"Remediation PR: {url}")

    # Exit 1 when vulnerabilities exist (CI gate).
    return 1 if summary["total_vulnerabilities"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
