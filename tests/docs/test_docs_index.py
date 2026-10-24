# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Every path named in docs/README.md must exist."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INDEX = REPO_ROOT / "docs" / "README.md"


def test_index_exists() -> None:
    assert INDEX.is_file(), "docs/README.md is missing"


def test_index_paths_exist() -> None:
    text = INDEX.read_text(encoding="utf-8")
    referenced = set(
        re.findall(
            r"`(docs/[^`]+|planning/[^`]+|SECURITY\.md|CONTRIBUTING\.md|AGENTS\.md)`",
            text,
        )
    )
    missing = []
    for entry in sorted(referenced):
        target = REPO_ROOT / entry.rstrip("/")
        if not target.exists():
            missing.append(entry)
    assert missing == [], f"docs/README.md points at missing paths: {missing}"
