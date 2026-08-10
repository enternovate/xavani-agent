# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Guard the provider-quirks reference table (backlog D95, S3-3).

docs/reference/provider-quirks.md documents provider quirks that the codebase
works around. Every row MUST cite a real source reference (``file:line``) so
the table stays honest: if a quirk's code reference is deleted, this test
fails and the row must be dropped or re-anchored.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOC = REPO_ROOT / "docs" / "reference" / "provider-quirks.md"

MIN_ROWS = 8

# Row = | Provider | Quirk | Symptom | Mitigation (in codebase) | Source ref |
_ROW_RE = re.compile(r"^\s*\|.*\|.*\|.*\|.*\|.*\|\s*$")
# First file:line ref in a row's Source ref column, e.g. agent/foo.py:123
_REF_RE = re.compile(r"([\w./-]+\.py):(\d+)")


def _table_rows() -> list[str]:
    lines = DOC.read_text(encoding="utf-8").splitlines()
    rows = []
    for line in lines:
        if not _ROW_RE.match(line):
            continue
        # Skip the header and separator rows (| --- | --- | ...).
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells or all(not c or set(c) <= {"-", ":", " "} for c in cells):
            continue
        if any(cell.lower() in {"provider", "quirk"} for cell in cells):
            continue
        rows.append(line)
    return rows


def test_doc_exists() -> None:
    assert DOC.is_file(), f"missing {DOC.relative_to(REPO_ROOT)}"


def test_at_least_min_rows() -> None:
    rows = _table_rows()
    assert len(rows) >= MIN_ROWS, (
        f"expected >= {MIN_ROWS} quirk rows, found {len(rows)}"
    )


def test_every_row_has_grounded_source_ref() -> None:
    for row in _table_rows():
        m = _REF_RE.search(row)
        assert m, f"row has no file:line source ref: {row!r}"
        rel_path, line_str = m.group(1), int(m.group(2))
        src = (REPO_ROOT / rel_path).resolve()
        assert src.is_file(), (
            f"source ref file missing for row {row!r}: {rel_path}"
        )
        total = len(src.read_text(encoding="utf-8").splitlines())
        assert 1 <= line_str <= total, (
            f"source ref line {line_str} out of range (file has {total} "
            f"lines) for {rel_path} in row {row!r}"
        )
