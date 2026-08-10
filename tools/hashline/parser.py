"""Pure-Python parser for the hashline patch language (ported from omp).

Implements the canonical grammar from omp's ``grammar.lark`` with strict
validation and no recovery:

* Sections are ``[PATH#TAG]`` where TAG is exactly four UPPERCASE hex chars.
* A header ending in ``:`` takes ``+TEXT`` body rows (verbatim final content);
  colonless ``PUT`` (register paste), ``CUT``, ``REM``, ``MV`` take none.
* ``*** Begin Patch`` / ``*** End Patch`` envelope is optional (the normal
  parser also accepts an unwrapped payload).
* Any deviation raises :class:`ParseError` with a helpful message and the
  1-indexed patch line it was detected on.

Accepted forms (N, M are 1-indexed original lines, ``[1-9]\\d*``):

``PUT N.=M:`` / ``PUT N*:`` / ``PUT <N:`` / ``PUT >N:`` / ``PUT >N*:`` /
``PUT >$:`` — body-taking; ``PUT <N [@r]`` / ``PUT >N [@r]`` / ``PUT >$ [@r]``
/ ``PUT N.=M @r`` / ``PUT N* @r`` — register pastes (no body); ``CUT N.=M`` /
``CUT N*`` with optional ``@r``; ``REM``; ``MV DEST``.
"""

from __future__ import annotations

import re
from typing import List, NoReturn, Optional, Tuple

from .model import (
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
    TAIL,
)

# One `[PATH#TAG]` header line. Path may contain anything except `#`; the tag
# is exactly four UPPERCASE hex chars (grammar.lark: file_hash /[0-9A-F]{4}/).
_HEADER_RE = re.compile(r"^\[(?P<path>[^#\r\n]+)#(?P<tag>[0-9A-F]{4})\]$")
# Line numbers are 1-indexed with no leading zeros: LID /[1-9]\d*/.
_LID = r"[1-9]\d*"
_RANGE_RE = re.compile(rf"^(?P<a>{_LID})\.=(?P<b>{_LID})$")
_BLOCK_RE = re.compile(rf"^(?P<a>{_LID})\*$")
_BEFORE_RE = re.compile(rf"^<(?P<a>{_LID})$")
_AFTER_BLOCK_RE = re.compile(rf"^>(?P<a>{_LID})\*$")
_AFTER_RE = re.compile(rf"^>(?P<a>{_LID})$")
# Register names: ASCII letters, digits, `_`, `-` (edit.md).
_REGISTER_RE = re.compile(r"^@([A-Za-z0-9_-]+)$")

_BEGIN_PATCH = "*** Begin Patch"
_END_PATCH = "*** End Patch"


class ParseError(Exception):
    """Raised when a hashline payload violates the canonical grammar.

    Attributes:
        message: human-readable description of the problem.
        line: 1-indexed patch line the error was detected on, or None.
    """

    def __init__(self, message: str, line: Optional[int] = None):
        self.message = message
        self.line = line
        if line is not None:
            message = f"hashline parse error (line {line}): {message}"
        super().__init__(message)


def parse(text: str) -> List[Section]:
    """Parse a hashline payload into an ordered list of Sections.

    Sections and ops keep their authored order; register ``CUT``/``PUT`` pairs
    may span sections.  Raises :class:`ParseError` on any grammar violation.
    """
    if not isinstance(text, str):
        raise TypeError(f"hashline payload must be str, got {type(text).__name__}")
    lines = [ln.rstrip("\r") for ln in text.split("\n")]
    sections: List[Section] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line == _BEGIN_PATCH:
            i += 1
            continue
        if line == _END_PATCH:
            for j in range(i + 1, n):
                if lines[j].strip():
                    raise ParseError(
                        f"unexpected content {lines[j]!r} after '{_END_PATCH}'", j + 1
                    )
            i = n
            continue
        if line.startswith("["):
            section, i = _parse_section(lines, i)
            sections.append(section)
            continue
        raise ParseError(
            f"expected a '[PATH#TAG]' section header (or '{_BEGIN_PATCH}'); "
            f"found {line!r}",
            i + 1,
        )
    if not sections:
        raise ParseError("empty patch: no '[PATH#TAG]' sections found", 1)
    return sections


def _parse_section(lines: List[str], i: int) -> Tuple[Section, int]:
    """Parse one section starting at a header line; returns (section, next_i)."""
    header_line = lines[i]
    header_line_num = i + 1
    match = _HEADER_RE.match(header_line)
    if not match:
        raise ParseError(
            f"malformed section header {header_line!r}; expected "
            f"'[PATH#TAG]' with a four-UPPERCASE-hex tag",
            header_line_num,
        )
    path, tag = match.group("path"), match.group("tag")
    ops: List[Op] = []
    ranges: List[Tuple[int, int]] = []  # explicit spans, for overlap checks
    i += 1
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        # Next section, envelope markers, or EOF end this section's hunks.
        if line.startswith("[") or line in (_BEGIN_PATCH, _END_PATCH):
            break
        op, i = _parse_op(lines, i)
        ops.append(op)
        if isinstance(op, (PutRange, CutRange)):
            ranges.append((op.start, op.end))
    if not ops:
        raise ParseError(
            f"section [{path}#{tag}] contains no operations; "
            "every section needs at least one PUT/CUT/REM/MV hunk",
            header_line_num,
        )
    _check_overlaps(ranges, header_line)
    return Section(path=path, tag=tag, ops=ops), i


def _check_overlaps(ranges: List[Tuple[int, int]], header_line: str) -> None:
    """Reject two explicit ranges that target any of the same original lines."""
    ordered = sorted(ranges)
    for (start_a, end_a), (start_b, end_b) in zip(ordered, ordered[1:]):
        if start_b <= end_a:
            raise ParseError(
                f"overlapping ranges in section {header_line!r}: "
                f"[{start_a}..{end_a}] and [{start_b}..{end_b}] target the "
                "same original lines; split non-adjacent changes into "
                "separate hunks"
            )


def _parse_op(lines: List[str], i: int) -> Tuple[Op, int]:
    """Parse one hunk (PUT/CUT/REM/MV); returns (op, next_index)."""
    line = lines[i]
    if line.startswith("+"):
        raise ParseError(
            f"unexpected body row {line!r}: the preceding operation takes no "
            "body (CUT, register PUT, REM, MV take no '+TEXT' rows), or no "
            "body-taking 'PUT ...:' is open",
            i + 1,
        )
    if not line.strip().startswith(("PUT", "CUT", "REM", "MV")):
        _raise_unknown_op(line, i + 1)
    if line.strip() == "REM":
        return RemoveFile(), i + 1
    if line.startswith("MV "):
        dest_raw = line[3:].strip()
        if not dest_raw:
            raise ParseError("'MV' requires a destination path", i + 1)
        return MoveFile(_unquote_dest(dest_raw)), i + 1
    if line.startswith("PUT "):
        return _parse_put(lines, i)
    if line.startswith("CUT "):
        return _parse_cut(lines, i)
    _raise_unknown_op(line, i + 1)


def _raise_unknown_op(line: str, line_num: int) -> NoReturn:
    if line.startswith("@@"):
        raise ParseError(
            f"unified-diff hunk header {line!r} is not a hashline operation; "
            "hashline ranges delete, bodies are '+TEXT' final content",
            line_num,
        )
    if line.startswith("-"):
        raise ParseError(
            f"unified-diff '-old' row {line!r} is not valid here; hashline "
            "bodies are final content ('+TEXT' rows), never before/after pairs",
            line_num,
        )
    if line.startswith(("---", "+++")):
        raise ParseError(
            f"unified-diff file marker {line!r} is not a hashline operation",
            line_num,
        )
    raise ParseError(
        f"unknown operation {line!r}; expected PUT/CUT/REM/MV or a "
        "'+TEXT' body row under a body-taking 'PUT ...:'",
        line_num,
    )


def _parse_put(lines: List[str], i: int) -> Tuple[Op, int]:
    line = lines[i]
    tokens = line[4:].split(" ")
    locator = tokens[0]
    register: Optional[str] = None
    colon = locator.endswith(":")
    if colon:
        locator = locator[:-1]
    if len(tokens) > 1:
        reg_tok = tokens[1]
        if len(tokens) > 2:
            raise ParseError(
                f"trailing content after register in {line!r}", i + 1
            )
        if reg_tok.endswith(":"):
            raise ParseError(
                f"{line!r}: a register PUT takes no body rows — remove the "
                "':' header",
                i + 1,
            )
        reg_match = _REGISTER_RE.match(reg_tok)
        if not reg_match:
            raise ParseError(
                f"invalid register {reg_tok!r} in {line!r}; register names "
                "are ASCII letters, digits, '_' or '-'",
                i + 1,
            )
        register = reg_match.group(1)
        if colon:
            raise ParseError(
                f"{line!r}: a register PUT takes no body rows — remove the "
                "':' header",
                i + 1,
            )

    range_match = _RANGE_RE.match(locator)
    if range_match:
        start, end = int(range_match.group("a")), int(range_match.group("b"))
        if end < start:
            raise ParseError(
                f"reversed range in {line!r}: {start} > {end} — ranges are "
                "inclusive and ordered (N.=M with N <= M)",
                i + 1,
            )
        if colon:
            body, next_i = _read_body(lines, i)
            return PutRange(start, end, body), next_i
        if register is not None:
            return PutRange(start, end, None, register), i + 1
        raise ParseError(
            f"{line!r}: span paste requires a register "
            f"('PUT {start}.={end} @name')",
            i + 1,
        )

    block_match = _BLOCK_RE.match(locator)
    if block_match:
        anchor = int(block_match.group("a"))
        if colon:
            body, next_i = _read_body(lines, i)
            return PutBlock(anchor, body), next_i
        if register is not None:
            return PutBlock(anchor, None, register), i + 1
        raise ParseError(
            f"{line!r}: block paste requires a register ('PUT {anchor}* @name')",
            i + 1,
        )

    before_match = _BEFORE_RE.match(locator)
    if before_match:
        anchor = int(before_match.group("a"))
        if colon:
            body, next_i = _read_body(lines, i)
            return InsertBefore(anchor, body), next_i
        return Paste(anchor, register, after=False), i + 1

    after_block_match = _AFTER_BLOCK_RE.match(locator)
    if after_block_match:
        anchor = int(after_block_match.group("a"))
        if colon:
            body, next_i = _read_body(lines, i)
            return InsertAfter(anchor, body, block=True), next_i
        return Paste(anchor, register, after=True, block=True), i + 1

    after_match = _AFTER_RE.match(locator)
    if after_match:
        anchor = int(after_match.group("a"))
        if colon:
            body, next_i = _read_body(lines, i)
            return InsertAfter(anchor, body), next_i
        return Paste(anchor, register, after=True), i + 1

    if locator == ">$":  # tail gap: PUT >$: (body) / PUT >$ [@r] (paste)
        if colon:
            body, next_i = _read_body(lines, i)
            return AppendTail(body), next_i
        return Paste(TAIL, register, after=True), i + 1

    raise ParseError(f"unknown PUT target {locator!r} in {line!r}", i + 1)


def _parse_cut(lines: List[str], i: int) -> Tuple[Op, int]:
    line = lines[i]
    tokens = line[4:].split(" ")
    locator = tokens[0]
    register: Optional[str] = None
    if locator.endswith(":"):
        raise ParseError(
            f"{line!r}: CUT takes no body rows — remove the ':' header", i + 1
        )
    if len(tokens) > 1:
        reg_tok = tokens[1]
        if len(tokens) > 2:
            raise ParseError(
                f"trailing content after register in {line!r}", i + 1
            )
        reg_match = _REGISTER_RE.match(reg_tok)
        if not reg_match:
            raise ParseError(
                f"invalid register {reg_tok!r} in {line!r}; register names "
                "are ASCII letters, digits, '_' or '-'",
                i + 1,
            )
        register = reg_match.group(1)

    range_match = _RANGE_RE.match(locator)
    if range_match:
        start, end = int(range_match.group("a")), int(range_match.group("b"))
        if end < start:
            raise ParseError(
                f"reversed range in {line!r}: {start} > {end} — ranges are "
                "inclusive and ordered (N.=M with N <= M)",
                i + 1,
            )
        return CutRange(start, end, register), i + 1

    block_match = _BLOCK_RE.match(locator)
    if block_match:
        return CutBlock(int(block_match.group("a")), register), i + 1

    raise ParseError(
        f"unknown CUT target {locator!r} in {line!r}; expected 'N.=M' or 'N*'",
        i + 1,
    )


def _read_body(lines: List[str], i: int) -> Tuple[List[str], int]:
    """Collect consecutive '+TEXT' rows after a body-taking header at line i.

    Every row is verbatim content after the '+'; '+' alone is a blank line.
    Returns (body_rows, index_after_last_row).
    """
    body: List[str] = []
    j = i + 1
    while j < len(lines) and lines[j].startswith("+"):
        body.append(lines[j][1:])
        j += 1
    if not body:
        header = lines[i]
        offender = lines[j] if j < len(lines) else "<end of input>"
        if isinstance(offender, str) and offender.startswith(("-", "@@", "---", "+++")):
            raise ParseError(
                f"{header!r} requires '+TEXT' body rows but found "
                f"unified-diff artifact {offender!r}",
                i + 1,
            )
        raise ParseError(
            f"{header!r} has an empty body; expected at least one '+TEXT' row "
            "(use CUT to delete, not an empty PUT)",
            i + 1,
        )
    return body, j


def _unquote_dest(dest: str) -> str:
    """Strip one layer of surrounding quotes (' or \") and backslash escapes.

    Mirrors omp's scanMoveDest: destinations containing spaces are quoted.
    """
    if len(dest) >= 2 and dest[0] == dest[-1] and dest[0] in ("'", '"'):
        inner = dest[1:-1]
        out: List[str] = []
        k = 0
        while k < len(inner):
            ch = inner[k]
            if ch == "\\" and k + 1 < len(inner):
                out.append(inner[k + 1])
                k += 2
            else:
                out.append(ch)
                k += 1
        return "".join(out)
    return dest


__all__ = ["ParseError", "parse"]
