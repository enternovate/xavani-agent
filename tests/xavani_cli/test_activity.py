# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for xavani_cli/activity.py formatting."""

from xavani_cli.activity import activity, banner_line, detail, format_duration


def test_format_duration_seconds():
    assert format_duration(2.84) == "2.8s"
    assert format_duration(0) == "0.0s"


def test_format_duration_minutes():
    assert format_duration(64) == "1m04s"
    assert format_duration(605.3) == "10m05s"


def test_format_duration_negative_clamps_to_zero():
    assert format_duration(-3) == "0.0s"


def test_activity_running_line_has_ellipsis():
    line = activity("patch", "cli.py", running=True)
    assert line.startswith("  ┊ 🔧 ")
    assert "patch" in line
    assert "cli.py" in line
    assert line.rstrip().endswith("…")


def test_activity_done_line_has_duration():
    line = activity("terminal", "pytest -q", seconds=5.12)
    assert "💻" in line
    assert "5.1s" in line
    assert "…" not in line


def test_unknown_verb_gets_bullet_icon():
    assert "•" in activity("transmogrify", running=True)


def test_detail_is_indented_deeper_than_gutter():
    line = detail("note")
    assert line.startswith("  ┊    ")


def test_banner_line_has_icon_prefix():
    assert banner_line("done", icon="✅") == "✅ done"
