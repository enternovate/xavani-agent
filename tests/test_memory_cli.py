# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""S3-6 (E106): ``xavani memory`` CLI subcommands.

Covers view/stats/diagnose/clear/enqueue: exit codes, output, the
``--yes`` guard on clear, and that enqueue actually persists.
"""

from __future__ import annotations

import pytest

from xavani_memory.cli import main
from xavani_memory.manager import MemoryManager


@pytest.fixture
def memory_dir(tmp_path):
    return tmp_path / "memory"


@pytest.fixture
def seeded(memory_dir):
    m = MemoryManager(memory_dir=memory_dir, auto_maintenance=False)
    m.set_session("cli-test")
    m.remember(user_input="first seeded memory entry", agent_response="ok", outcome="done")
    m.remember(user_input="second seeded memory entry", agent_response="ok", outcome="done")
    try:
        m.stop_maintenance()
    except Exception:
        pass
    return memory_dir


def test_view_lists_entries(seeded, capsys):
    rc = main(["view", "--memory-dir", str(seeded)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "first seeded memory entry" in out
    assert "second seeded memory entry" in out


def test_stats_reflects_stored_entries(seeded, capsys):
    rc = main(["stats", "--memory-dir", str(seeded)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "2 episodes" in out


def test_diagnose_reports_healthy_stores(seeded, capsys):
    rc = main(["diagnose", "--memory-dir", str(seeded)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "OK" in out


def test_clear_without_yes_refuses(seeded, capsys):
    rc = main(["clear", "--memory-dir", str(seeded)])
    out = capsys.readouterr().out
    assert rc != 0
    assert "--yes" in out
    m = MemoryManager(memory_dir=seeded, auto_maintenance=False)
    assert len(m.episodic.get_recent(limit=100)) == 2


def test_clear_with_yes_empties(seeded, capsys):
    rc = main(["clear", "--yes", "--memory-dir", str(seeded)])
    capsys.readouterr()
    assert rc == 0
    m = MemoryManager(memory_dir=seeded, auto_maintenance=False)
    assert m.episodic.archive_stats()["total"] == 0


def test_enqueue_adds_entry(memory_dir, capsys):
    rc = main(["enqueue", "a freshly enqueued memory", "--memory-dir", str(memory_dir)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Enqueued" in out
    m = MemoryManager(memory_dir=memory_dir, auto_maintenance=False)
    recent = m.episodic.get_recent(limit=10)
    assert any("freshly enqueued" in ep["user_input"] for ep in recent)


def test_no_subcommand_is_usage_error(capsys):
    rc = main([])
    assert rc != 0
    assert "usage" in capsys.readouterr().err.lower()


def test_diagnose_reports_corrupt_store_without_traceback(tmp_path, monkeypatch, capsys):
    """A corrupt store must yield a graceful diagnose report, exit 1, no traceback."""
    from pathlib import Path
    from xavani_memory import cli as memory_cli
    memory_dir = Path(tmp_path)
    # Corrupt one store file so MemoryManager construction would raise.
    (memory_dir / "episodic.db").write_bytes(b"not a sqlite database at all")
    (memory_dir / "procedural.db").write_bytes(b"")

    code = memory_cli.main(["--memory-dir", str(memory_dir), "diagnose"])
    out = capsys.readouterr().out
    assert code == 1
    assert "episodic.db" in out
    assert "Traceback" not in out


def test_corrupt_store_other_commands_fail_gracefully(tmp_path, capsys):
    """view/stats on a corrupt store exit 1 with guidance, never traceback."""
    from pathlib import Path
    from xavani_memory import cli as memory_cli
    memory_dir = Path(tmp_path)
    (memory_dir / "episodic.db").write_bytes(b"garbage not sqlite")
    (memory_dir / "procedural.db").write_bytes(b"garbage not sqlite")

    code = memory_cli.main(["--memory-dir", str(memory_dir), "stats"])
    err = capsys.readouterr().err
    assert code == 1
    assert "diagnose" in err
    assert "Traceback" not in err
