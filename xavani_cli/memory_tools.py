# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Memory bank tools: retain, recall, reflect, learn, memory_edit.

The bank lives at ``~/.xavani/memories/bank/`` as one markdown file per
fact, id-named with a timestamp prefix so entries sort chronologically
and stay individually addressable for edit and invalidate.
"""

from __future__ import annotations

import os
import re
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

_BANK_DIRNAME = Path("memories") / "bank"
_ID_RE = re.compile(r"^mem-\d{8}-\d{6}-[0-9a-f]{4}\.md$")
_SLUG_RE = re.compile(r"[^a-z0-9]+")


class MemoryError(ValueError):
    pass


def bank_dir() -> Path:
    override = os.environ.get("XAVANI_MEMORY_BANK")
    if override:
        return Path(override)
    return Path.home() / ".xavani" / _BANK_DIRNAME


def uuid_suffix() -> str:
    return uuid.uuid4().hex[:6]


def _unique_path(base: Path, tag: str) -> Path:
    while True:
        candidate = base / f"{_new_id(tag)}.md"
        if not candidate.exists():
            return candidate


def _new_id(tag: str) -> str:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    return f"mem-{stamp}-{uuid_suffix()}-{_slug(tag)[:12]}"


def _slug(text: str) -> str:
    return _SLUG_RE.sub("-", text.lower()).strip("-")


def retain(
    text: str,
    *,
    tag: str = "fact",
    source: Optional[str] = None,
    directory: Optional[Path] = None,
) -> Dict[str, Any]:
    """Queue one durable fact as a bank entry; returns the record."""
    if not text or not text.strip():
        raise MemoryError("memory text must be a non-empty string")
    base = directory or bank_dir()
    base.mkdir(parents=True, exist_ok=True)
    path = _unique_path(base, tag or "fact")
    entry_id = path.stem
    provenance = f"\n\nsource: {source}\n" if source else "\n"
    body = (
        f"# {entry_id}\n\n{text.strip()}\n{provenance}"
        f"retained: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
    )
    path = base / f"{entry_id}.md"
    path.write_text(body, encoding="utf-8")
    return {"id": entry_id, "path": str(path), "text": text.strip()}


def entries(directory: Optional[Path] = None) -> List[Dict[str, Any]]:
    """All bank entries oldest-first: id, path, text."""
    base = directory or bank_dir()
    if not base.is_dir():
        return []
    out: List[Dict[str, Any]] = []
    for path in sorted(base.glob("mem-*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        match = re.search(r"^# (mem-\S+)\n", text)
        out.append({
            "id": match.group(1) if match else path.stem,
            "path": str(path),
            "text": _body_text(text),
        })
    return out


def _body_text(raw: str) -> str:
    lines = raw.splitlines()
    body = [ln for ln in lines[1:] if not ln.startswith(("source:", "retained:"))]
    return "\n".join(body).strip()


def recall(
    query: str,
    *,
    limit: int = 5,
    directory: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Search the bank case-insensitively; every term must hit."""
    terms = [t.lower() for t in query.split() if t.strip()]
    hits: List[Dict[str, Any]] = []
    for entry in entries(directory):
        haystack = (entry["id"] + "\n" + entry["text"]).lower()
        if all(term in haystack for term in terms):
            hits.append(entry)
            if len(hits) >= limit:
                break
    return hits


def reflect(
    topic: str,
    *,
    limit: int = 10,
    directory: Optional[Path] = None,
) -> Dict[str, Any]:
    """Collect everything the bank holds on a topic for synthesis."""
    hits = recall(topic, limit=limit, directory=directory)
    return {
        "topic": topic,
        "entry_count": len(hits),
        "entries": [e["text"] for e in hits],
    }


def learn(
    lesson: str,
    *,
    context: Optional[str] = None,
    directory: Optional[Path] = None,
) -> Dict[str, Any]:
    """Capture a reusable lesson tagged for future skill promotion."""
    record = retain(
        f"lesson: {lesson}" if not lesson.startswith("lesson:") else lesson,
        tag="lesson",
        source=context,
        directory=directory,
    )
    return record


def memory_edit(
    entry_id: str,
    *,
    new_text: Optional[str] = None,
    invalidate: bool = False,
    directory: Optional[Path] = None,
) -> Dict[str, Any]:
    """Update or invalidate one entry by id."""
    base = directory or bank_dir()
    path = base / f"{entry_id}.md"
    if not path.is_file():
        raise MemoryError(f"no bank entry {entry_id}")
    if invalidate:
        raw = path.read_text(encoding="utf-8")
        path.write_text(
            raw.replace("\n\nsource:", "\ninvalidated: yes\nsource:", 1)
            if "invalidated:" not in raw
            else raw,
            encoding="utf-8",
        )
        return {"id": entry_id, "action": "invalidated"}
    if not new_text or not new_text.strip():
        raise MemoryError("new_text must be a non-empty string when not invalidating")
    raw = path.read_text(encoding="utf-8")
    updated = re.sub(
        r"(^# mem-\S+\n\n).*", r"\1" + new_text.strip().replace("\\", "\\\\") + "\n",
        raw,
        count=1,
        flags=re.DOTALL,
    )
    path.write_text(updated, encoding="utf-8")
    return {"id": entry_id, "action": "updated", "text": new_text.strip()}


def promote_candidates(directory: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Lesson-tagged entries eligible for promotion to a skill."""
    return [e for e in entries(directory) if e["id"].find("lesson") != -1]


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    import json
    import sys

    parser = argparse.ArgumentParser(prog="memory_bank")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_retain = sub.add_parser("retain")
    p_retain.add_argument("text")
    p_retain.add_argument("--tag", default="fact")
    p_recall = sub.add_parser("recall")
    p_recall.add_argument("query")
    p_reflect = sub.add_parser("reflect")
    p_reflect.add_argument("topic")
    p_learn = sub.add_parser("learn")
    p_learn.add_argument("lesson")
    p_edit = sub.add_parser("edit")
    p_edit.add_argument("entry_id")
    p_edit.add_argument("--text", default=None)
    p_edit.add_argument("--invalidate", action="store_true")

    args = parser.parse_args(argv)
    try:
        if args.cmd == "retain":
            payload: Any = retain(args.text, tag=args.tag)
        elif args.cmd == "recall":
            payload = recall(args.query)
        elif args.cmd == "reflect":
            payload = reflect(args.topic)
        elif args.cmd == "learn":
            payload = learn(args.lesson)
        else:
            payload = memory_edit(
                args.entry_id, new_text=args.text, invalidate=args.invalidate
            )
    except MemoryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
