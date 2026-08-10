# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for website/scripts/gen_tool_reference.py (Task 20).

Runs the generator as a subprocess against a temp outdir so the tests
exercise the real CLI surface (imports, discovery, file emission).
"""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "website" / "scripts" / "gen_tool_reference.py"


def run_gen(outdir: Path, limit: int) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--outdir", str(outdir), "--limit", str(limit)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=300,
    )


def test_generates_limit_pages_with_required_content(tmp_path):
    out = tmp_path / "ref"
    res = run_gen(out, 3)
    assert res.returncode == 0, f"stderr: {res.stderr}"

    pages = sorted(out.glob("*.md"))
    assert len(pages) == 3, f"expected 3 pages, got {[p.name for p in pages]}"

    for page in pages:
        text = page.read_text(encoding="utf-8")
        parts = text.split("---")
        assert len(parts) >= 3, f"{page.name}: missing closed frontmatter"
        frontmatter = parts[1]
        assert "id:" in frontmatter
        assert "title:" in frontmatter
        assert "sidebar_label:" in frontmatter
        body = "---".join(parts[2:])
        assert body.strip(), f"{page.name}: empty body"
        assert "## Parameters" in body, f"{page.name}: missing Parameters section"


def test_known_tool_page_contains_its_toolset(tmp_path):
    out = tmp_path / "ref"
    res = run_gen(out, 3)
    assert res.returncode == 0, f"stderr: {res.stderr}"

    page = (out / "browser_cdp.md").read_text(encoding="utf-8")
    assert "browser-cdp" in page


def test_writes_category_file(tmp_path):
    out = tmp_path / "ref"
    res = run_gen(out, 3)
    assert res.returncode == 0, f"stderr: {res.stderr}"

    cat = out / "_category_.json"
    assert cat.exists()
    assert '"Tools"' in cat.read_text(encoding="utf-8")
