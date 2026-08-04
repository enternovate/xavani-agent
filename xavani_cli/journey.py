"""``xavani journey`` — what Xavani has learned, on a timeline.

The journey CLI renders the learning graph (``agent.learning_graph``) as a
readable text timeline: learned skills, memory cards, and the edges between
them. It supports list, stats, detail, delete, and edit subcommands.

The TUI ``/journey`` overlay and the web dashboard draw the same data via
``build_learning_graph()``; this module is the text surface.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone


def _ts_display(ts) -> str:
    if not ts:
        return "—"
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        return "—"


def _fmt_graph(payload: dict) -> str:
    """Render the graph payload as plain text lines."""
    lines: list[str] = []
    stats = payload.get("stats", {})
    lines.append("✦ JOURNEY — learned skills & memories")
    lines.append(f"  learned skills: {stats.get('learned_skills', 0)}   "
                 f"memory cards: {stats.get('memory_nodes', 0)}   "
                 f"skill edges: {stats.get('related_edges', 0)}   "
                 f"memory→skill edges: {stats.get('memory_skill_edges', 0)}")
    clusters = payload.get("clusters", [])
    if clusters:
        lines.append("  clusters: " + ", ".join(f"{c['category']}×{c['count']}" for c in clusters[:8]))
    lines.append("")
    nodes = payload.get("nodes", [])
    for node in sorted(nodes, key=lambda n: (n.get("timestamp") or 0), reverse=True):
        kind = node.get("kind", "skill")
        glyph = "🧠" if kind == "memory" else "✦"
        label = node.get("label", node.get("id", "?"))
        ts = _ts_display(node.get("timestamp"))
        if kind == "memory":
            src = node.get("memorySource", "memory")
            lines.append(f"  {glyph} [{src}] {label}  ({ts})")
        else:
            used = f" · used {node.get('useCount', 0)}×" if node.get("useCount") else ""
            created = " · agent-created" if node.get("createdBy") == "agent" else ""
            lines.append(f"  {glyph} {label}  ({ts}){used}{created}")
    edges = payload.get("edges", [])
    if edges:
        lines.append("")
        lines.append(f"  connections ({len(edges)}):")
        for e in edges[:25]:
            lines.append(f"    {e.get('source')} ↔ {e.get('target')}")
    return "\n".join(lines)


def cmd_journey(args: argparse.Namespace) -> int:
    """CLI entry point for ``xavani journey``."""
    action = getattr(args, "journey_action", None)
    if action == "list":
        from agent.learning_graph import build_learning_graph
        print(_fmt_graph(build_learning_graph()))
        return 0
    if action == "stats":
        from agent.learning_graph import build_learning_graph
        payload = build_learning_graph()
        stats = payload.get("stats", {})
        for key in sorted(stats):
            print(f"  {key}: {stats[key]}")
        return 0
    if action == "detail":
        from agent.learning_mutations import node_detail
        result = node_detail(args.node)
        if not result.get("ok"):
            print(f"error: {result.get('message', 'failed')}")
            return 1
        print(f"--- {result.get('label')} ({result.get('kind')}) ---")
        print(result.get("content", ""))
        return 0
    if action == "delete":
        from agent.learning_mutations import delete_node
        result = delete_node(args.node)
        print(result.get("message", ""))
        return 0 if result.get("ok") else 1
    if action == "edit":
        from agent.learning_mutations import edit_node
        content = args.content
        if not content and args.file:
            from pathlib import Path
            content = Path(args.file).read_text(encoding="utf-8")
        result = edit_node(args.node, content or "")
        print(result.get("message", ""))
        return 0 if result.get("ok") else 1
    # Default: list
    from agent.learning_graph import build_learning_graph
    print(_fmt_graph(build_learning_graph()))
    return 0


def build_journey_parser(parent) -> argparse.ArgumentParser:
    """Attach the journey subparser to the xavani CLI."""
    sub = parent.add_subparsers(dest="journey_action")
    sub.add_parser("list", help="Show the learning graph as a timeline")
    sub.add_parser("stats", help="Show learning-graph statistics")
    p_del = sub.add_parser("delete", help="Delete/archive a node (skill name or memory:<source>:<index>)")
    p_del.add_argument("node")
    p_del2 = sub.add_parser("detail", help="Show a node's current content")
    p_del2.add_argument("node")
    p_edit = sub.add_parser("edit", help="Edit a node's content")
    p_edit.add_argument("node")
    p_edit.add_argument("content", nargs="?", default="")
    p_edit.add_argument("--file", default="", help="Read new content from a file")
    return sub


__all__ = ["cmd_journey", "build_journey_parser", "_fmt_graph"]
