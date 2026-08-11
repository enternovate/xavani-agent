# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""D08: dependency provenance report tests."""

import json

from xavani_cli.deps_provenance import (
    build_provenance_report,
    cmd_deps_provenance,
    render_report,
)
import pytest

pytestmark = pytest.mark.integration


def test_report_covers_direct_dependencies():
    rows = build_provenance_report()
    names = {r["name"] for r in rows}
    assert "openai" in names
    assert "httpx" in names
    assert "fire" in names
    assert len(rows) >= 15


def test_every_row_has_version_and_source():
    for row in build_provenance_report():
        assert row["version"], row["name"]
        assert row["source"], row["name"]
        assert row["audit_date"], row["name"]


def test_render_report_has_header_and_rows():
    rows = build_provenance_report()
    text = render_report(rows)
    assert "Dependency provenance" in text
    assert "source" in text.lower()
    assert "audit" in text.lower()
    assert "openai" in text


def test_cmd_json_output(capsys):
    import argparse

    args = argparse.Namespace(json=True)
    assert cmd_deps_provenance(args) == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert isinstance(payload, list)
    assert any(r["name"] == "openai" for r in payload)
