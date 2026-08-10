#!/usr/bin/env python3

# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Generate per-tool Docusaurus reference pages.

One page per registered tool lands in ``website/docs/reference/tools/``:

    website/docs/reference/tools/<tool-name>.md
    website/docs/reference/tools/_category_.json   (single "Tools" category)

Each page carries frontmatter (id, title, sidebar_label) plus the tool's
one-line description, a parameter table derived from the JSON schema
(name / type / required / description), its toolset, and a return-value
note.  The reference model is omp's per-tool docs (docs/tools/): Source /
Inputs / Outputs / Flow / Limits / Errors, adapted to what the registry
actually declares.

Regenerate (run from the repo root):

    python3 website/scripts/gen_tool_reference.py

Discovery covers every *registered* tool (built-in toolsets plus any
plugin/MCP tools that were registered at import time), not just the tools
whose availability checks pass on the current machine, so the docs are a
complete reference.  Tools are ordered by name for deterministic output.

Generated pages are intentionally not committed to git -- run the command
above to refresh them.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Make repo root importable so ``model_tools`` / ``tools.registry`` resolve
# regardless of the directory the script is invoked from.
REPO = Path(__file__).resolve().parent.parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

DEFAULT_OUTDIR = REPO / "website" / "docs" / "reference" / "tools"

_CATEGORY_JSON = {
    "label": "Tools",
    "position": 5,
    "link": {
        "type": "generated-index",
        "description": "Auto-generated reference pages for every registered tool.",
    },
}


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def discover_tool_entries() -> List[Any]:
    """Import all tool modules and return every registered ToolEntry, sorted by name."""
    from tools.registry import discover_builtin_tools, registry

    discover_builtin_tools()
    return sorted(registry._snapshot_entries(), key=lambda entry: entry.name)


# ---------------------------------------------------------------------------
# Schema rendering helpers
# ---------------------------------------------------------------------------


def _render_type(spec: Dict[str, Any]) -> str:
    """Render a JSON-schema property type as a compact string."""
    if not isinstance(spec, dict):
        return "any"
    if "anyOf" in spec:
        return " | ".join(
            _render_type(item) for item in spec["anyOf"] if isinstance(item, dict)
        ) or "any"
    ptype = spec.get("type", "any")
    if ptype == "array" and isinstance(spec.get("items"), dict):
        return f"array<{_render_type(spec['items'])}>"
    if "enum" in spec:
        values = ", ".join(repr(v) for v in spec["enum"])
        return f"{ptype} (one of: {values})"
    return str(ptype)


def _parameter_rows(schema: Dict[str, Any]) -> Tuple[List[Tuple[str, str, str, str]], bool]:
    """Return ``(rows, has_parameters)`` from a tool's JSON schema.

    Each row is ``(name, type, required, description)`` sorted by name.
    """
    params = schema.get("parameters") or {}
    props = params.get("properties") or {}
    required = set(params.get("required") or [])
    rows = []
    for name in sorted(props):
        spec = props[name] or {}
        description = (spec.get("description") or "").replace("\n", " ").strip()
        rows.append(
            (
                name,
                _render_type(spec),
                "Yes" if name in required else "No",
                description or "—",
            )
        )
    return rows, bool(props)


def _entry_description(entry: Any) -> str:
    """One-line tool description with newlines collapsed."""
    description = (entry.description or "").strip() or (entry.schema.get("description") or "").strip()
    return " ".join(description.split())


def _has_return_declaration(schema: Dict[str, Any]) -> bool:
    """True when the schema declares a return shape (rare; schemas usually don't)."""
    return any(key in schema for key in ("returns", "return", "output"))


# ---------------------------------------------------------------------------
# Page generation
# ---------------------------------------------------------------------------


def render_page(entry: Any) -> str:
    """Render the full markdown page for one tool entry."""
    name = entry.name
    description = _entry_description(entry)
    rows, has_params = _parameter_rows(entry.schema)

    lines = [
        "---",
        f"id: {name}",
        f'title: "{name}"',
        f'sidebar_label: "{name}"',
        "---",
        "",
        f"# {name}",
        "",
        f"> {description}",
        "",
        "## Parameters",
        "",
    ]
    if has_params:
        lines += [
            "| Name | Type | Required | Description |",
            "| --- | --- | --- | --- |",
        ]
        for pname, ptype, required, pdesc in rows:
            # Escape pipes inside table cells so descriptions render literally.
            pdesc = pdesc.replace("|", "\\|")
            lines.append(f"| `{pname}` | `{ptype}` | {required} | {pdesc} |")
    else:
        lines.append("This tool takes no parameters.")
    lines += [
        "",
        "## Toolset",
        "",
        f"`{entry.toolset}`",
        "",
        "## Return value",
        "",
    ]
    if _has_return_declaration(entry.schema):
        lines.append("Declared by the tool schema (see tool source for the exact shape).")
    else:
        lines.append("The tool schema does not declare a return shape.")
    lines.append("")
    return "\n".join(lines)


def write_pages(entries: List[Any], outdir: Path) -> List[Path]:
    """Write one .md per entry plus the category file; return written paths."""
    outdir.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []
    for entry in entries:
        page = outdir / f"{entry.name}.md"
        page.write_text(render_page(entry), encoding="utf-8")
        written.append(page)
    (outdir / "_category_.json").write_text(
        json.dumps(_CATEGORY_JSON, indent=2) + "\n", encoding="utf-8"
    )
    written.append(outdir / "_category_.json")
    return written


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Generate per-tool Docusaurus reference pages.")
    parser.add_argument(
        "--outdir",
        type=Path,
        default=DEFAULT_OUTDIR,
        help="Output directory (default: website/docs/reference/tools)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only write the first N tools (for testing)",
    )
    args = parser.parse_args(argv)

    entries = discover_tool_entries()
    if args.limit is not None:
        entries = entries[: args.limit]

    written = write_pages(entries, args.outdir)
    print(f"Generated {len(entries)} tool page(s) + category file in {args.outdir}")
    for path in written[: args.limit or len(written)]:
        print(f"  {path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
