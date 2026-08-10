"""Hashline — line-anchored patch grammar and parser (ported from omp).

The flagship omp recipe: ``[PATH#TAG]`` sections holding ``PUT`` / ``CUT`` /
``REM`` / ``MV`` hunks against ORIGINAL (tagged-snapshot) line numbers, with
``+TEXT`` body rows as verbatim final content.  This package ports the
grammar (``grammar.lark``) and a strict pure-Python parser; application of
the parsed sections is out of scope here.

Example::

    from tools.hashline import parse

    sections = parse(
        "[greet.py#A1B2]\\n"
        "PUT 1*:\\n"
        "+@cache\\n"
        "+def greet(name):\\n"
        '+    print(f"Hi, {name}")\\n'
    )
"""

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
from .parser import ParseError, parse

__all__ = [
    "TAIL",
    "AppendTail",
    "CutBlock",
    "CutRange",
    "InsertAfter",
    "InsertBefore",
    "MoveFile",
    "Op",
    "ParseError",
    "Paste",
    "PutBlock",
    "PutRange",
    "RemoveFile",
    "Section",
    "parse",
]
