# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Security audit command (C03).

Runs a small set of local checks and prints a PASS/WARN report.
No network access; nothing is read from or uploaded to the internet.
"""

from __future__ import annotations

import stat
from pathlib import Path
from typing import Dict, List

from xavani_cli.config import get_config_path, get_env_path, load_config


def _check_redact_secrets() -> Dict[str, str]:
    """Check that secret redaction is enabled in config.yaml."""
    try:
        cfg = load_config()
    except Exception:
        return {
            "check": "secret redaction",
            "status": "WARN",
            "detail": "config.yaml is unreadable",
        }
    sec = (cfg or {}).get("security", {}) or {}
    if sec.get("redact_secrets"):
        return {
            "check": "secret redaction",
            "status": "PASS",
            "detail": "security.redact_secrets is enabled",
        }
    return {
        "check": "secret redaction",
        "status": "WARN",
        "detail": "security.redact_secrets is not enabled",
    }


def _check_file_permissions(path: Path, label: str) -> Dict[str, str]:
    """Check that a sensitive file is not group or world readable."""
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
    except OSError:
        return {
            "check": label,
            "status": "WARN",
            "detail": f"{path} was not found",
        }
    if mode & 0o077 == 0:
        return {
            "check": label,
            "status": "PASS",
            "detail": f"{path} is private (mode {mode:o})",
        }
    return {
        "check": label,
        "status": "WARN",
        "detail": f"{path} is readable by others (mode {mode:o})",
    }


def run_security_audit() -> List[Dict[str, str]]:
    """Run the audit and return one result dict per check."""
    results = [_check_redact_secrets()]
    results.append(_check_file_permissions(get_env_path(), ".env permissions"))
    results.append(_check_file_permissions(get_config_path(), "config.yaml permissions"))
    return results


def cmd_security_audit(args) -> None:
    """Argparse entry point: run the audit and print the report."""
    failures = 0
    for result in run_security_audit():
        status = result["status"]
        if status == "PASS":
            print(f"  \u2713 {result['check']}: {result['detail']}")
        else:
            failures += 1
            print(f"  \u26a0 {result['check']}: {result['detail']}")
    print()
    if failures:
        print(f"Security audit finished: {failures} item(s) need attention.")
    else:
        print("Security audit finished: all checks passed.")
