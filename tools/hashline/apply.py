"""Apply engine for hashline patches (Task 13, ported from omp's apply logic).

Turns parsed :class:`~tools.hashline.model.Section` objects into concrete
in-memory file mutations against the per-session
:class:`~tools.hashline.snapshots.SnapshotStore`, fail-fast:

* EVERY section is validated before ANY write — tag resolution, anchor
  bounds, seen-line enforcement (ops may only touch lines inside the
  snapshot's recorded ``visible_ranges``), register availability, in-section
  range conflicts and byte-identical no-ops are all detected up front, so a
  bad section later in the patch leaves every earlier file untouched.
* Ops are then applied in file order, purely in memory: line numbers refer
  to the ORIGINAL snapshot content and the working copy is renumbered after
  every op (the file is never re-read between ops).  A mid-application
  failure (unexpected) is reported as ``ApplyResult.error`` with the prefix
  already applied — no rollback is attempted yet.
* On success each touched file is recorded back into the store with a fresh
  content tag (``store.record``); ``REM`` invalidates the entry; ``MV``
  records under the destination and invalidates the source.

Block ops (``PUT N*`` / ``CUT N*`` / ``PUT >N*``) need tree-sitter block
resolution (Task 14) and raise :class:`ApplyError` with guidance to use
explicit line ranges instead.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union, cast

from .model import (
    TAIL,
    AppendTail,
    CutBlock,
    CutRange,
    InsertAfter,
    InsertBefore,
    MoveFile,
    Op,
    Paste,
    PutBlock,
    PutRange,
    RemoveFile,
    Section,
)
from .snapshots import Snapshot, SnapshotStore

__all__ = ["ApplyError", "ApplyResult", "FileResult", "apply_sections"]


class ApplyError(Exception):
    """Raised when a hashline patch cannot be applied.

    Validation failures (bad anchors, unseen lines, empty registers,
    byte-identical no-ops, block ops, stale tags) raise this BEFORE any file
    is written, so nothing is partially applied.
    """


@dataclass(frozen=True)
class FileResult:
    """Outcome for one section's file, in patch order.

    ``tag`` is the fresh content tag of the recorded snapshot (``None`` for
    a removed file), ``preview`` the full new file content, and ``action``
    one of ``"edit"`` / ``"remove"`` / ``"move"`` (for a move, ``path`` is
    the destination).
    """

    path: str
    tag: Optional[str]
    preview: str
    action: str


@dataclass(frozen=True)
class ApplyResult:
    """Outcome of an :func:`apply_sections` call.

    ``results`` holds one :class:`FileResult` per section in file order.
    ``error`` is set only when a write failed mid-way after validation
    passed: the files already applied are reported in ``results`` (prefix
    applied, no rollback).  ``warnings`` carries non-fatal notes (stale
    tag applied against, overwritten MV destination).
    """

    results: List[FileResult] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None


# -- validation / simulation helpers ----------------------------------------


def _block_msg(path: str) -> str:
    return (
        f"[{path}]: block operations (PUT N*: / PUT >N* / CUT N*) are not "
        "resolvable yet — they need tree-sitter block resolution (Task 14); "
        "use explicit line ranges (PUT N.=M: / CUT N.=M) instead"
    )


def _covered(lo: int, hi: int, visible: Tuple[Tuple[int, int], ...]) -> bool:
    return any(a <= lo and hi <= b for (a, b) in visible)


def _check_line_visible(path: str, line: int, visible, total: int) -> None:
    if line < 1 or line > total:
        raise ApplyError(
            f"[{path}]: line {line} is out of range — the file has {total} "
            "line(s); re-read the file"
        )
    if not _covered(line, line, visible):
        raise ApplyError(
            f"[{path}]: line {line} was not visible in your read — edits may "
            f"only target lines you have seen (visible ranges {visible}); "
            "re-read the file"
        )


def _check_range_visible(
    path: str, start: int, end: int, visible, total: int
) -> None:
    if start < 1 or end < start or end > total:
        raise ApplyError(
            f"[{path}]: range {start}..{end} is out of range — the file has "
            f"{total} line(s); re-read the file"
        )
    if not _covered(start, end, visible):
        raise ApplyError(
            f"[{path}]: range {start}..{end} is not fully inside the lines "
            f"you have seen (visible ranges {visible}); re-read the file"
        )


def _require_register(name: Optional[str], state, path: str) -> List[str]:
    if name is None:
        if state["anon"] is None:
            raise ApplyError(
                f"[{path}]: anonymous register is empty — CUT a range first "
                "(CUT N.=M) before a register PUT"
            )
        return state["anon"]
    if name not in state["named"]:
        raise ApplyError(
            f"[{path}]: register @{name} is empty — CUT into it first "
            f"(CUT N.=M @{name})"
        )
    return state["named"][name]


def _store_register(state, name: Optional[str], captured: List[str]) -> None:
    if name is None:
        state["anon"] = captured
    else:
        state["named"][name] = captured


def _find(work, path: str, lineno: int) -> int:
    for i, entry in enumerate(work):
        if entry[0] == "o" and entry[1] == lineno:
            return i
    raise ApplyError(
        f"[{path}]: original line {lineno} no longer exists — it was already "
        "deleted by an earlier CUT/PUT in this section; re-read the file"
    )


def _ensure_no_inserts(work, i: int, j: int, path: str) -> None:
    if any(entry[0] == "i" for entry in work[i : j + 1]):
        raise ApplyError(
            f"[{path}]: range crosses content inserted earlier in this "
            "section; fold the insertions into one PUT and re-read the file"
        )


def _apply_op(work, op: Op, path: str, visible, total: int, state) -> None:
    if isinstance(op, (PutBlock, CutBlock)):
        raise ApplyError(_block_msg(path))
    if isinstance(op, PutRange):
        _check_range_visible(path, op.start, op.end, visible, total)
        body = op.body if op.body is not None else _require_register(
            op.register, state, path
        )
        i, j = _find(work, path, op.start), _find(work, path, op.end)
        _ensure_no_inserts(work, i, j, path)
        work[i : j + 1] = [("i", ln) for ln in body]
    elif isinstance(op, InsertBefore):
        _check_line_visible(path, op.line, visible, total)
        i = _find(work, path, op.line)
        work[i:i] = [("i", ln) for ln in op.body]
    elif isinstance(op, InsertAfter):
        if op.block:
            raise ApplyError(_block_msg(path))
        _check_line_visible(path, op.line, visible, total)
        i = _find(work, path, op.line)
        work[i + 1 : i + 1] = [("i", ln) for ln in op.body]
    elif isinstance(op, AppendTail):
        work.extend(("i", ln) for ln in op.body)
    elif isinstance(op, CutRange):
        _check_range_visible(path, op.start, op.end, visible, total)
        i, j = _find(work, path, op.start), _find(work, path, op.end)
        _ensure_no_inserts(work, i, j, path)
        captured = [entry[2] for entry in work[i : j + 1]]
        del work[i : j + 1]
        _store_register(state, op.register, captured)
    elif isinstance(op, Paste):
        if op.block:
            raise ApplyError(_block_msg(path))
        body = _require_register(op.register, state, path)
        if op.anchor == TAIL:
            work.extend(("i", ln) for ln in body)
        else:
            assert isinstance(op.anchor, int)
            _check_line_visible(path, op.anchor, visible, total)
            i = _find(work, path, op.anchor)
            if op.after:
                work[i + 1 : i + 1] = [("i", ln) for ln in body]
            else:
                work[i:i] = [("i", ln) for ln in body]
    elif isinstance(op, (RemoveFile, MoveFile)):
        raise AssertionError("REM/MV are handled at section level")  # pragma: no cover


def _simulate_section(
    sec: Section, base: Snapshot, state
) -> Tuple[str, Optional[Union[str, Tuple[str, str]]]]:
    """Dry-run a section's ops; returns (action, value) without any writes.

    ``action`` is ``"edit"`` (value = new content str), ``"remove"``
    (value = None) or ``"move"`` (value = (dest, new content str)).  Any
    problem raises :class:`ApplyError` so the caller writes nothing.
    """
    path = sec.path
    try:
        text = base.content.decode("utf-8")
    except UnicodeDecodeError:
        raise ApplyError(
            f"[{path}#{base.tag}]: snapshot is not valid UTF-8; cannot apply"
        )
    has_trailing = text.endswith("\n")
    raw = text.split("\n")
    if has_trailing:
        raw = raw[:-1]
    total = len(raw)
    visible = base.visible_ranges
    work = [("o", i + 1, ln) for i, ln in enumerate(raw)]

    # REM/MV are terminal: at most one, and only as the last op.
    term: Optional[int] = None
    is_remove = False
    for idx, op in enumerate(sec.ops):
        if isinstance(op, (RemoveFile, MoveFile)):
            if term is not None:
                raise ApplyError(
                    f"[{path}]: REM and MV are mutually exclusive — a "
                    "section may delete or move its file, not both"
                )
            term = idx
            is_remove = isinstance(op, RemoveFile)
    if term is not None and term != len(sec.ops) - 1:
        kind = "REM" if is_remove else "MV"
        raise ApplyError(
            f"[{path}]: {kind} must be the last operation in its section"
        )

    for op in (sec.ops if term is None else sec.ops[:term]):
        _apply_op(work, op, path, visible, total, state)

    new_text = "\n".join(entry[-1] for entry in work)
    if has_trailing:
        new_text += "\n"

    if is_remove:
        return ("remove", None)
    if term is not None:
        dest = sec.ops[term].dest  # type: ignore[union-attr]
        if dest == path:
            raise ApplyError(
                f"[{path}]: MV {path!r} onto itself changes nothing — "
                "drop the MV or pick a different destination"
            )
        return ("move", (dest, new_text))

    if new_text.encode("utf-8") == base.content:
        raise ApplyError(
            f"[{path}#{base.tag}]: edit is a byte-identical no-op — nothing "
            "changed; fix the PUT/CUT hunks or drop the section"
        )
    return ("edit", new_text)


def _resolve_base(sec: Section, store: SnapshotStore) -> Snapshot:
    entry = store.by_hash(sec.path, sec.tag)
    if entry is not None:
        return entry
    head = store.get(sec.path)
    if head is None:
        raise ApplyError(
            f"[{sec.path}#{sec.tag}]: no snapshot recorded for this path — "
            "read the file first (re-read the file)"
        )
    raise ApplyError(
        f"[{sec.path}#{sec.tag}]: snapshot tag {sec.tag} not found — the "
        f"file changed since your read (latest tag {head.tag}); re-read the "
        "file"
    )


def _full_ranges(content: str) -> Tuple[Tuple[int, int], ...]:
    lines = content.split("\n")
    if content.endswith("\n"):
        lines = lines[:-1]
    return ((1, len(lines)),) if lines else ()


def _commit(
    sec: Section, base: Snapshot, sim: Tuple[str, object], store: SnapshotStore
) -> Tuple[FileResult, List[str]]:
    warnings: List[str] = []
    head = store.get(sec.path)
    if head is not None and head.tag != base.tag:
        warnings.append(
            f"[{sec.path}#{sec.tag}]: applying against an older recorded "
            f"snapshot (current head {head.tag}); the file changed since "
            "your read"
        )
    action, value = sim
    if action == "edit":
        content = cast(str, value)
        tag = store.record(sec.path, content, ranges=_full_ranges(content))
        return FileResult(sec.path, tag, content, "edit"), warnings
    if action == "remove":
        store.invalidate(sec.path)
        return FileResult(sec.path, None, "", "remove"), warnings
    dest, content = cast(Tuple[str, str], value)
    if store.get(dest) is not None:
        warnings.append(
            f"MV {sec.path!r} -> {dest!r}: destination already has a "
            "recorded snapshot; overwriting"
        )
    tag = store.record(dest, content, ranges=_full_ranges(content))
    store.invalidate(sec.path)
    return FileResult(dest, tag, content, "move"), warnings


# -- public API --------------------------------------------------------------


def apply_sections(sections: List[Section], store: SnapshotStore) -> ApplyResult:
    """Validate and apply every section against ``store``; returns an
    :class:`ApplyResult`.

    Raises :class:`ApplyError` when ANY section fails validation — in that
    case nothing is written at all (fail fast).  Once validation passes,
    sections are committed in file order; an unexpected mid-way failure is
    returned as ``ApplyResult.error`` with the already-applied prefix in
    ``results`` (no rollback is attempted yet).
    """
    if not sections:
        raise ApplyError("nothing to apply: no sections provided")

    # Phase 1 — dry-run every section (registers persist across sections in
    # call order).  Any ApplyError here means ZERO writes have happened.
    state: Dict[str, object] = {"anon": None, "named": {}}
    bases: List[Snapshot] = []
    sims = []
    for sec in sections:
        base = _resolve_base(sec, store)
        bases.append(base)
        sims.append(_simulate_section(sec, base, state))

    # Phase 2 — commit in file order.
    results: List[FileResult] = []
    warnings: List[str] = []
    for sec, base, sim in zip(sections, bases, sims):
        try:
            fr, warns = _commit(sec, base, sim, store)
        except Exception as exc:  # pragma: no cover - store-level failure
            return ApplyResult(
                results=results,
                warnings=warnings,
                error=(
                    f"apply failed mid-way after {len(results)} file(s); "
                    f"prefix applied, no rollback yet: {exc}"
                ),
            )
        results.append(fr)
        warnings.extend(warns)
    return ApplyResult(results=results, warnings=warnings)
