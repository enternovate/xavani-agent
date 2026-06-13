# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Outcome patterns — record decisions, compare them to what happened (v1.0.0 ①).

This closes the user's loop: *"compare the pattern brought forth by outcomes of
decisions."* Each collapsed decision is recorded with the branch it chose; later,
when the real result is known, :func:`record` stores the realised score, and
:func:`compare` summarises which chosen-branch archetypes actually paid off. Those
deltas feed ``xavani_operator/learn.py`` so the operator's opportunity weights
move toward decisions that work and away from ones that don't.

Persistence is a simple JSON list (one record per decision). Pure Python,
deterministic, zero-LLM (R10).

Record fields: ``decision_id`` (str), ``chosen_id`` (str),
``branch_ids`` (list[str]), ``realized`` (float 0..1), ``ts`` (float epoch seconds).
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from xavani_operator.quantum.state import Decision


@dataclass
class OutcomeRecord:
    """One decision and the result it produced."""

    decision_id: str
    chosen_id: str
    branch_ids: list[str] = field(default_factory=list)
    realized: float = 0.0
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "OutcomeRecord":
        fields = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in d.items() if k in fields})


def load(path: str | Path) -> list[OutcomeRecord]:
    """Load all outcome records from ``path`` (empty list if absent/corrupt)."""
    p = Path(path)
    if not p.exists():
        return []
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(raw, list):
        return []
    return [OutcomeRecord.from_dict(d) for d in raw if isinstance(d, dict)]


def record(
    path: str | Path,
    decision: Decision,
    realized: float,
    *,
    decision_id: str | None = None,
    ts: float | None = None,
) -> OutcomeRecord:
    """Append a record of ``decision`` and its realised score to ``path``."""
    rec = OutcomeRecord(
        decision_id=decision_id or decision.chosen.id,
        chosen_id=decision.chosen.id,
        branch_ids=[b.id for b, _ in decision.ranked],
        realized=float(realized),
        ts=ts if ts is not None else time.time(),
    )
    records = load(path)
    records.append(rec)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps([r.to_dict() for r in records], indent=2), encoding="utf-8")
    return rec


def compare(records: list[OutcomeRecord]) -> dict[str, float]:
    """Mean realised score per chosen branch id. Deterministic.

    The returned mapping is what ``learn`` consumes: a chosen branch whose mean
    realised score is high should have its weight nudged up, and vice-versa.
    """
    sums: dict[str, float] = {}
    counts: dict[str, int] = {}
    for r in records:
        sums[r.chosen_id] = sums.get(r.chosen_id, 0.0) + r.realized
        counts[r.chosen_id] = counts.get(r.chosen_id, 0) + 1
    return {cid: sums[cid] / counts[cid] for cid in sorted(sums)}
