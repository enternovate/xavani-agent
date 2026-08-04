# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""G04: proactive disclosure — "here's what might break".

Before a risky operation runs, disclose the risks and provide a
rollback plan. Pattern-based (no LLM): known risky command families map
to their failure modes and recovery paths. Disclosure is advisory text
the agent can include in its reply — it never blocks anything.

Usage::

    from xavani_cli.proactive_disclosure import disclosure_for

    block = disclosure_for("git push --force origin main")
    if block:
        print(block["risks"])
        print(block["rollback"])
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

# (regex, risks: list, rollback: list) — first match wins.
_DISCLOSURE_RULES: List[Tuple[re.Pattern, List[str], List[str]]] = [
    (
        re.compile(r"\bgit\s+push\s+.*--force\b|\bgit\s+push\s+-f\b"),
        [
            "Force-push rewrites remote history — other clones lose commits.",
            "CI and open PRs based on the old history can break.",
        ],
        [
            "If you must undo: `git push --force-with-lease` restores the prior commit with `git reset --hard <sha>` locally first.",
            "Confirm the remote before pushing — there is no undo on shared branches.",
        ],
    ),
    (
        re.compile(r"\brm\s+-rf\b"),
        [
            "Recursive delete is unrecoverable — no trash, no undo.",
            "A typo in the path (trailing slash, missing dot) removes the wrong tree.",
        ],
        [
            "Double-check the resolved path before running.",
            "If available, restore from git (untracked files are lost) or a backup/snapshot.",
        ],
    ),
    (
        re.compile(r"\bdd\s+(?:if=[^\s]+\s+)?of="),
        [
            "Writing directly to a device can destroy a disk or partition.",
            "Wrong device paths are not recoverable.",
        ],
        [
            "Verify the target device with `lsblk` / `diskutil list` first.",
            "There is no rollback for device-level writes.",
        ],
    ),
    (
        re.compile(r"\bdocker\s+(rm\s+-f|volume\s+rm|system\s+prune)\b"),
        [
            "Forced container/volume removal destroys container state and named volumes.",
            "`system prune` deletes unused containers, networks, and (with -a) images.",
        ],
        [
            "Back up named volumes before removal (docker run --volumes-from + tar).",
            "Recreate containers from your compose file or run command.",
        ],
    ),
    (
        re.compile(r"\b(?:DROP|TRUNCATE|DELETE\s+FROM)\b", re.IGNORECASE),
        [
            "Database deletion is permanent unless the engine keeps a transaction log.",
            "A missing WHERE clause removes every row.",
        ],
        [
            "Wrap in a transaction: BEGIN; <statement>; ROLLBACK; to test first.",
            "Restore from the latest backup if the statement already ran.",
        ],
    ),
    (
        re.compile(r"\b(?:chmod|chown)\s+[-R]?\s*[0-7]{3,4}\b"),
        [
            "Recursive permission changes can lock the user out of their own files.",
            "chown to the wrong owner breaks service access.",
        ],
        [
            "Record the original mode (`stat -c %a <path>`) before changing.",
            "Restore with the recorded mode or re-run with the correct owner.",
        ],
    ),
    (
        re.compile(r"\bkill\s+-9\b|\bpkill\s+-9\b"),
        [
            "SIGKILL cannot be caught — the process gets no chance to flush state.",
            "Databases and editors can corrupt open files.",
        ],
        [
            "Prefer SIGTERM (`kill <pid>`) and wait for graceful shutdown.",
            "Check for stale locks after the kill and remove them if the process is gone.",
        ],
    ),
]


def disclosure_for(command: str) -> Optional[Dict[str, Any]]:
    """Return a disclosure block for a risky command, or None.

    The returned dict has ``category``, ``risks`` (list), and
    ``rollback`` (list) keys. Commands outside the known risk families
    return None (no disclosure needed).
    """
    if not command:
        return None
    for pattern, risks, rollback in _DISCLOSURE_RULES:
        if pattern.search(command):
            return {
                "category": pattern.pattern[:60],
                "risks": risks,
                "rollback": rollback,
            }
    return None


def format_disclosure(disclosure: Dict[str, Any]) -> str:
    """Render a disclosure dict as a compact advisory block."""
    lines = [
        "",
        "⚠️  Proactive disclosure — before you run this, consider:",
    ]
    for risk in disclosure.get("risks", []):
        lines.append(f"  • {risk}")
    lines.append("  Rollback plan:")
    for step in disclosure.get("rollback", []):
        lines.append(f"    - {step}")
    lines.append("")
    return "\n".join(lines)


def disclosure_categories() -> List[str]:
    """All known disclosure categories, for docs and tests."""
    return [pattern.pattern for pattern, _, _ in _DISCLOSURE_RULES]
