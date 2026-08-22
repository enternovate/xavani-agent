# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""SESSION_HANDOFF.md generator: durable resume state for any project.

Pure logic plus one write entry point. The generator takes structured
sections and renders the standard handoff format: running processes,
output files, state checklist, decisions, preferences, and a
copy-paste resume prompt.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional


def render_handoff(sections: Dict[str, Any]) -> str:
    """Render handoff markdown from structured sections.

    Recognized keys: title, date, processes (rows), outputs (lines),
    state_done (lines), state_pending (lines), decisions (lines),
    preferences (lines), resume_prompt (str).
    """
    title = sections.get("title", "Session Handoff")
    lines = [f"# {title}", ""]
    if sections.get("date"):
        lines += [f"Date: {sections['date']}", ""]
    processes = sections.get("processes") or []
    if processes:
        lines += ["## Running Processes", "", "| PID | Description | Output | ETA |",
                  "|-----|-------------|--------|-----|"]
        for row in processes:
            lines.append(
                f"| {row.get('pid', '-')} | {row.get('description', '-')} "
                f"| {row.get('output', '-')} | {row.get('eta', '-')} |"
            )
        lines.append("")
    outputs = sections.get("outputs") or []
    if outputs:
        lines += ["## Output Files", ""]
        lines += [f"- **{o}**" for o in outputs]
        lines.append("")
    done = sections.get("state_done") or []
    pending = sections.get("state_pending") or []
    if done or pending:
        lines += ["## State", ""]
        lines += [f"- [x] {item}" for item in done]
        lines += [f"- [ ] {item}" for item in pending]
        lines.append("")
    decisions = sections.get("decisions") or []
    if decisions:
        lines += ["## Key Decisions Made This Session", ""]
        lines += [f"- {d}" for d in decisions]
        lines.append("")
    preferences = sections.get("preferences") or []
    if preferences:
        lines += ["## User Preferences (for next agent)", ""]
        lines += [f"- {p}" for p in preferences]
        lines.append("")
    prompt = sections.get("resume_prompt")
    if prompt:
        lines += [
            "## Resume Prompt",
            "",
            "Copy-paste this to resume:",
            "",
            "```",
            prompt.strip(),
            "```",
            "",
        ]
    return "\n".join(lines).rstrip("\n") + "\n"


def default_date() -> str:
    return time.strftime("%Y-%m-%d")


def write_handoff(
    path: Path,
    sections: Dict[str, Any],
) -> Path:
    """Write the rendered handoff; never silently overwrite.

    An existing file gains a numeric suffix before the extension so a
    fresh handoff can never destroy prior state.
    """
    target = path
    counter = 1
    while target.exists():
        target = path.with_name(f"{path.stem}-{counter}{path.suffix}")
        counter += 1
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_handoff({**sections, "date": sections.get("date", default_date())}),
                      encoding="utf-8")
    return target


def collect_session_state(
    *,
    project_path: Optional[str] = None,
    extra_decisions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Minimal self-state snapshot for quick handoffs."""
    decisions = list(extra_decisions or [])
    return {
        "title": "Session Handoff",
        "project_path": project_path or str(Path.cwd()),
        "decisions": decisions,
    }
