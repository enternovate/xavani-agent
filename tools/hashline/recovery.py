"""Stale-tag recovery for hashline sections (Task 17, ported from omp's recovery.ts).

When the file on disk drifts after the model's last read, the section's
4-hex snapshot tag no longer matches the store head.  Recovery replays the
recorded snapshot chain to decide whether the model's anchors can be
re-mapped onto the drifted content UNIQUELY and SAFELY:

* The anchored range's original lines are extracted from the recorded
  version the tag refers to (``store.by_hash``).
* That exact line run is located in the drifted head content, with the
  surrounding context (one line above / one line below, when present)
  verified.
* The whole window's line counts must match the drifted file: if any
  window line is duplicated elsewhere, the interpretation is not provable
  and recovery FAILS CLOSED with re-read guidance.

Conservative by design: recovery only applies when the snapshot chain
proves a unique safe result.  Anything ambiguous, missing, or drifted in
the anchored region raises :class:`ApplyError` telling the model to
re-read the file.  Block ops, inserts, pastes and REM/MV are NOT recovered
in this version — they need the same anchor provenance and are safer to
re-read (Task 18+ may extend this).
"""

from __future__ import annotations

from dataclasses import replace
from typing import List, Optional, Tuple

from .model import (
    CutRange,
    Op,
    PutRange,
    Section,
)
from .snapshots import Snapshot, SnapshotStore

__all__ = ["recover_section", "recoverable_ops"]

#: Ops that recovery can re-anchor.  Everything else fails closed.
recoverable_ops = (PutRange, CutRange)


def _apply_error(path: str, tag: str, why: str):
    """Late-import ApplyError to avoid the apply<->recovery cycle."""
    from .apply import ApplyError

    return ApplyError(f"[{path}#{tag}]: {why}")


def _window_lines(
    old: Snapshot, start: int, end: int
) -> Tuple[List[str], int, int]:
    """Extract ``(lines, ctx_above_start, ctx_below_end)`` around old range.

    ``start``/``end`` are 1-indexed inclusive ORIGINAL lines.  The returned
    ``lines`` list is the anchor window INCLUDING one context line above
    (when ``start > 1``) and one context line below (when ``end < total``),
    so the caller can verify both the run and its surroundings.
    """
    text = old.content.decode("utf-8")
    raw = text.split("\n")
    if text.endswith("\n"):
        raw = raw[:-1]
    total = len(raw)
    ctx_above = start - 1 if start > 1 else 0
    ctx_below = end + 1 if end < total else total + 1
    # Inclusive slice from ctx_above..ctx_below (1-indexed, both optional).
    lo = ctx_above if ctx_above else start
    hi = ctx_below if ctx_below <= total else end
    return raw[lo - 1 : hi], ctx_above, ctx_below


def _find_unique_run(
    window: List[str], ctx_above: int, ctx_below: int, new: Snapshot
) -> Optional[int]:
    """Locate ``window`` in ``new`` at a unique, context-verified offset.

    Returns the 1-indexed line in ``new`` where the window's ANCHOR start
    maps (the window includes optional context lines above/below, so the
    anchor start is ``offset + (1 if ctx_above else 0)``).  ``None`` when
    the run is absent, duplicated, or its context counts cannot be proven
    unique.
    """
    text = new.content.decode("utf-8")
    raw = text.split("\n")
    if text.endswith("\n"):
        raw = raw[:-1]
    # The anchor = window minus optional context rows (one above, one below).
    has_above = ctx_above != 0
    has_below = ctx_below <= len(raw)
    anchor = window[1:] if has_above else window
    if has_below:
        anchor = anchor[:-1]
    run_len = len(anchor)
    if run_len == 0:
        return None

    matches: List[int] = []
    for i in range(len(raw) - run_len + 1):
        if raw[i : i + run_len] == anchor:
            # Verify context lines when present.
            ok = True
            if has_above:
                above = window[0]
                if i == 0 or raw[i - 1] != above:
                    ok = False
            if ok and has_below:
                below = window[-1]
                if i + run_len >= len(raw) or raw[i + run_len] != below:
                    ok = False
            if ok:
                matches.append(i)
    if len(matches) != 1:
        return None
    # Count-provenance: each distinct line in the FULL window must occur in
    # the new file exactly as many times as it occurs in the window, or the
    # interpretation is not unique (omp: fail closed on ambiguity).
    from collections import Counter

    window_counts = Counter(window)
    for line, count in window_counts.items():
        if raw.count(line) != count:
            return None
    offset = matches[0]
    return offset + (1 if has_above else 0)


def recover_section(
    sec: Section, store: SnapshotStore, head: Snapshot
) -> Section:
    """Return a re-anchored section targeting the drifted ``head``.

    Raises :class:`ApplyError` with re-read guidance when the anchors
    cannot be proven unique against the head.
    """
    old = store.by_hash(sec.path, sec.tag)
    if old is None:
        raise _apply_error(
            sec.path, sec.tag,
            "the recorded snapshot for this tag is no longer available; "
            "re-read the file",
        )

    new_ops: List[Op] = []
    for op in sec.ops:
        if isinstance(op, PutRange):
            window, above, below = _window_lines(old, op.start, op.end)
            mapped = _find_unique_run(window, above, below, head)
            if mapped is None:
                raise _apply_error(
                    sec.path, sec.tag,
                    "the file changed since your read and recovery cannot "
                    "prove where the anchored lines moved; re-read the file",
                )
            shift = mapped - op.start
            new_ops.append(replace(op, start=op.start + shift, end=op.end + shift))
        elif isinstance(op, CutRange):
            window, above, below = _window_lines(old, op.start, op.end)
            mapped = _find_unique_run(window, above, below, head)
            if mapped is None:
                raise _apply_error(
                    sec.path, sec.tag,
                    "the file changed since your read and recovery cannot "
                    "prove where the anchored lines moved; re-read the file",
                )
            shift = mapped - op.start
            new_ops.append(replace(op, start=op.start + shift, end=op.end + shift))
        else:
            raise _apply_error(
                sec.path, sec.tag,
                "this operation type is not recoverable after the file "
                "changed; re-read the file and re-issue the edit with fresh "
                "anchors",
            )

    return replace(sec, ops=tuple(new_ops))
