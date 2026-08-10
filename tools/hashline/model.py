"""Pure data model for the hashline patch language (ported from omp).

Each dataclass is a frozen, comparable value object.  Bodies are tuples of
lines — the VERBATIM final content of the touched region, never unified-diff
before/after pairs.  ``body=None`` on :class:`PutRange` / :class:`PutBlock`
marks a register paste (the bodyless ``PUT N.=M @name`` / ``PUT N* @name``
forms); ``register`` names the source register in that case.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple, Union

#: File-tail marker used as the ``anchor`` of a tail paste (``PUT >$``).
TAIL = "$"


@dataclass(frozen=True)
class PutRange:
    """``PUT N.=M:`` — replace original lines N..M (inclusive) with ``body``.

    With ``body=None`` and a ``register`` this is the span-paste form
    ``PUT N.=M @name`` (replace the range with the register's captured lines).
    """

    start: int
    end: int
    body: Optional[Tuple[str, ...]] = None
    register: Optional[str] = None


@dataclass(frozen=True)
class PutBlock:
    """``PUT N*:`` — replace the syntactic block beginning on line N.

    With ``body=None`` and a ``register`` this is the block-paste form
    ``PUT N* @name``.
    """

    line: int
    body: Optional[Tuple[str, ...]] = None
    register: Optional[str] = None


@dataclass(frozen=True)
class InsertBefore:
    """``PUT <N:`` — insert body rows immediately before line N (``<1`` = file head)."""

    line: int
    body: Tuple[str, ...]


@dataclass(frozen=True)
class InsertAfter:
    """``PUT >N:`` — insert body rows immediately after line N.

    ``block=True`` marks the ``PUT >N*:`` form: insert after the END of the
    syntactic block beginning at line N (resolved at apply time).
    """

    line: int
    body: Tuple[str, ...]
    block: bool = False


@dataclass(frozen=True)
class AppendTail:
    """``PUT >$:`` — append body rows at file tail."""

    body: Tuple[str, ...]


@dataclass(frozen=True)
class CutRange:
    """``CUT N.=M [@name]`` — delete and capture lines N..M (inclusive)."""

    start: int
    end: int
    register: Optional[str] = None


@dataclass(frozen=True)
class CutBlock:
    """``CUT N* [@name]`` — delete and capture the block beginning at line N."""

    line: int
    register: Optional[str] = None


@dataclass(frozen=True)
class Paste:
    """Register paste into a gap: ``PUT <N`` / ``PUT >N`` / ``PUT >$``.

    ``anchor`` is the 1-indexed line, or the string ``"$"`` for file tail.
    ``after=False`` for ``<N`` (before the anchor), ``after=True`` for ``>N``
    and ``>$``.  ``register=None`` means the batch-local anonymous register.
    ``block=True`` marks ``PUT >N* @name`` (paste after the resolved block).
    """

    anchor: Union[int, str]
    register: Optional[str] = None
    after: bool = True
    block: bool = False


@dataclass(frozen=True)
class RemoveFile:
    """``REM`` — delete the whole section file."""


@dataclass(frozen=True)
class MoveFile:
    """``MV DEST`` — move/rename the section file to ``dest``."""

    dest: str


Op = Union[
    PutRange,
    PutBlock,
    InsertBefore,
    InsertAfter,
    AppendTail,
    CutRange,
    CutBlock,
    Paste,
    RemoveFile,
    MoveFile,
]


@dataclass(frozen=True)
class Section:
    """One ``[PATH#TAG]`` section: its ops in authored order.

    ``tag`` is the 4-uppercase-hex snapshot tag from the latest read/search;
    it is REQUIRED on every section.
    """

    path: str
    tag: str
    ops: Tuple[Op, ...] = ()


__all__ = [
    "TAIL",
    "AppendTail",
    "CutBlock",
    "CutRange",
    "InsertAfter",
    "InsertBefore",
    "MoveFile",
    "Op",
    "Paste",
    "PutBlock",
    "PutRange",
    "RemoveFile",
    "Section",
]
