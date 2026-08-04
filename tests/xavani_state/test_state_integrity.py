# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""A12: hash-based state file integrity verification.

State files carry a SHA-256 sidecar (<path>.sha256). Reads verify the
sidecar. Mismatch raises StateCorruptionError. SQLite databases use
PRAGMA quick_check, cached on (path, size, mtime_ns).
"""

import os
import sqlite3
from pathlib import Path

import pytest

import xavani_state_integrity as xsi
from xavani_state_integrity import (
    StateCorruptionError,
    clear_sqlite_verify_cache,
    read_state_file,
    sha256_file,
    state_hash_path,
    verify_sqlite_db,
    verify_state_file,
    write_state_file,
    write_state_hash,
)


# ── sha256_file ──────────────────────────────────────────────────────


def test_sha256_file_matches_hashlib(tmp_path):
    p = tmp_path / "state.json"
    p.write_bytes(b"hello state")
    import hashlib

    assert sha256_file(p) == hashlib.sha256(b"hello state").hexdigest()


def test_sha256_file_reads_in_chunks(tmp_path):
    p = tmp_path / "big.bin"
    p.write_bytes(b"x" * 200_000)  # crosses the 64KB chunk boundary
    assert sha256_file(p) == sha256_file(p)


# ── sidecar hash write/verify ────────────────────────────────────────


def test_write_state_hash_creates_sidecar(tmp_path):
    p = tmp_path / "state.json"
    p.write_text('{"a": 1}', encoding="utf-8")
    sidecar = write_state_hash(p)
    assert sidecar == state_hash_path(p)
    assert sidecar.exists()
    assert sidecar.read_text(encoding="utf-8").strip() == sha256_file(p)


def test_verify_state_file_passes_when_unchanged(tmp_path):
    p = tmp_path / "state.yaml"
    p.write_text("a: 1\n", encoding="utf-8")
    write_state_hash(p)
    assert verify_state_file(p) == sha256_file(p)


def test_verify_state_file_raises_on_tamper(tmp_path):
    p = tmp_path / "state.yaml"
    p.write_text("a: 1\n", encoding="utf-8")
    write_state_hash(p)
    p.write_text("a: 2\n", encoding="utf-8")  # tampered
    with pytest.raises(StateCorruptionError) as ei:
        verify_state_file(p)
    assert "state.yaml" in str(ei.value)


def test_verify_state_file_returns_none_without_sidecar(tmp_path):
    p = tmp_path / "state.json"
    p.write_text("{}", encoding="utf-8")
    assert verify_state_file(p) is None


def test_verify_state_file_rearm_on_mismatch(tmp_path):
    p = tmp_path / "state.yaml"
    p.write_text("a: 1\n", encoding="utf-8")
    write_state_hash(p)
    p.write_text("a: 2\n", encoding="utf-8")
    # rearm rewrites the sidecar instead of raising
    assert verify_state_file(p, rearm_on_mismatch=True) == sha256_file(p)
    # now the new content verifies cleanly
    assert verify_state_file(p) == sha256_file(p)


def test_read_state_file_raises_on_tamper(tmp_path):
    p = tmp_path / "state.json"
    p.write_text("{}", encoding="utf-8")
    write_state_hash(p)
    p.write_bytes(b"corrupted")
    with pytest.raises(StateCorruptionError):
        read_state_file(p)


def test_write_state_file_roundtrip_updates_sidecar(tmp_path):
    p = tmp_path / "state.json"
    write_state_file(p, b'{"v": 1}')
    assert verify_state_file(p) == sha256_file(p)
    write_state_file(p, b'{"v": 2}')
    assert verify_state_file(p) == sha256_file(p)
    assert read_state_file(p) == b'{"v": 2}'


# ── SQLite quick_check ───────────────────────────────────────────────


def _make_sqlite_db(path, n_rows=10):
    """Create a real SQLite DB with a table and rows."""
    conn = sqlite3.connect(str(path))
    try:
        conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
        conn.executemany(
            "INSERT INTO t (v) VALUES (?)",
            [(f"value-{i}",) for i in range(n_rows)],
        )
        conn.commit()
    finally:
        conn.close()
    return path


def _corrupt_db_by_truncation(path):
    """Truncate a DB to half and drop WAL sidecars.

    Missing pages always fail PRAGMA quick_check, unlike mid-file byte
    flips which WAL-mode DBs hide (live frames live in the -wal file).
    """
    path = Path(path)
    for suffix in ("-wal", "-shm"):
        side = Path(str(path) + suffix)
        if side.exists():
            side.unlink()
    data = path.read_bytes()
    path.write_bytes(data[: len(data) // 2])
    clear_sqlite_verify_cache()


def _corrupt_db_by_page_size(path):
    """Corrupt the page-size field in the DB header (offset 16-17).

    Preserves file size and mtime — used by the cache test to prove the
    cache skips re-scanning unchanged (path, size, mtime) tuples.
    """
    path = Path(path)
    data = bytearray(path.read_bytes())
    data[16:18] = b"\xff\xff"  # invalid page size
    path.write_bytes(bytes(data))


def test_verify_sqlite_db_ok_on_healthy(tmp_path):
    db = _make_sqlite_db(tmp_path / "ok.db")
    clear_sqlite_verify_cache()
    assert verify_sqlite_db(db) == "ok"


def test_verify_sqlite_db_raises_on_corrupt(tmp_path):
    db = _make_sqlite_db(tmp_path / "corrupt.db")
    _corrupt_db_by_truncation(db)
    with pytest.raises(StateCorruptionError) as ei:
        verify_sqlite_db(db)
    assert "corrupt.db" in str(ei.value)


def test_verify_sqlite_db_raises_on_garbage(tmp_path):
    db = tmp_path / "garbage.db"
    db.write_bytes(b"this is not a sqlite database at all")
    clear_sqlite_verify_cache()
    with pytest.raises(StateCorruptionError):
        verify_sqlite_db(db)


def test_verify_sqlite_db_missing_file_returns_none(tmp_path):
    clear_sqlite_verify_cache()
    assert verify_sqlite_db(tmp_path / "nope.db") is None


def test_verify_sqlite_db_cache_skips_rescan(tmp_path):
    db = _make_sqlite_db(tmp_path / "cached.db")
    clear_sqlite_verify_cache()
    assert verify_sqlite_db(db) == "ok"
    # Corrupt the page-size field in place with identical size and
    # restore mtime — the cache must return the cached result without
    # rescanning.
    st = db.stat()
    _corrupt_db_by_page_size(db)
    os.utime(db, ns=(st.st_atime_ns, st.st_mtime_ns))
    assert verify_sqlite_db(db) == "ok"  # cached — no rescan
    # force=True rescans and detects the corruption
    with pytest.raises(StateCorruptionError):
        verify_sqlite_db(db, force=True)


def test_integrity_enabled_flag(monkeypatch):
    assert xsi.integrity_enabled() is True
    monkeypatch.setenv("XAVANI_SKIP_STATE_INTEGRITY", "1")
    assert xsi.integrity_enabled() is False


# ── SessionDB integration ────────────────────────────────────────────


def test_sessiondb_raises_on_corrupt_db(tmp_path):
    from xavani_state import SessionDB

    db_path = tmp_path / "state.db"
    db = SessionDB(db_path)
    db.create_session("s1", source="cli")
    db.append_message("s1", role="user", content="hello")
    # Close the connection so the file is not locked.
    db.close()

    _corrupt_db_by_truncation(db_path)

    with pytest.raises(StateCorruptionError):
        SessionDB(db_path)


def test_sessiondb_healthy_open_passes(tmp_path):
    from xavani_state import SessionDB

    db = SessionDB(tmp_path / "state.db")
    try:
        db.create_session("s1", source="cli")
    finally:
        db.close()


def test_sessiondb_skip_env_does_not_raise(monkeypatch, tmp_path):
    from xavani_state import SessionDB

    monkeypatch.setenv("XAVANI_SKIP_STATE_INTEGRITY", "1")
    db_path = tmp_path / "state.db"
    db = SessionDB(db_path)
    db.create_session("s1", source="cli")
    db.close()

    data = bytearray(db_path.read_bytes())
    mid = len(data) // 2
    data[mid : mid + 256] = b"\x00" * 256
    db_path.write_bytes(bytes(data))

    # Verification disabled — open succeeds (sqlite tolerates the byte
    # flip until the affected page is read).
    db2 = SessionDB(db_path)
    db2.close()


# ── Memory DB integration ────────────────────────────────────────────


def test_episodic_memory_raises_on_corrupt_db(tmp_path):
    from xavani_memory.episodic import EpisodicMemory

    db_path = tmp_path / "episodic.db"
    m = EpisodicMemory(db_path)
    m.store_episode(
        user_input="hello",
        agent_response="hi",
        session_id="s1",
    )
    _corrupt_db_by_truncation(db_path)

    with pytest.raises(StateCorruptionError):
        EpisodicMemory(db_path)


def test_procedural_memory_raises_on_corrupt_db(tmp_path):
    from xavani_memory.procedural import ProceduralMemory

    db_path = tmp_path / "procedural.db"
    m = ProceduralMemory(db_path)
    m.record_outcome(
        task_type="test",
        parameters={"a": 1},
        approach="x",
        result="ok",
        success=True,
    )
    _corrupt_db_by_truncation(db_path)

    with pytest.raises(StateCorruptionError):
        ProceduralMemory(db_path)


# ── config.yaml integration ──────────────────────────────────────────


def test_config_save_writes_sidecar_and_load_verifies(tmp_path, monkeypatch):
    from xavani_cli import config as cfg

    monkeypatch.setenv("XAVANI_HOME", str(tmp_path))
    # Reset per-path caches so the new XAVANI_HOME is read fresh.
    cfg._LOAD_CONFIG_CACHE.clear()
    cfg._RAW_CONFIG_CACHE.clear()

    cfg.save_config({"model": {"default": "test-model"}})
    config_path = tmp_path / "config.yaml"
    assert config_path.exists()
    sidecar = state_hash_path(config_path)
    assert sidecar.exists()
    assert sidecar.read_text(encoding="utf-8").strip() == sha256_file(config_path)

    # Normal load works.
    loaded = cfg.load_config()
    assert loaded["model"]["default"] == "test-model"


def test_config_tamper_warns_and_rearms(tmp_path, monkeypatch):
    from xavani_cli import config as cfg

    monkeypatch.setenv("XAVANI_HOME", str(tmp_path))
    cfg._LOAD_CONFIG_CACHE.clear()
    cfg._RAW_CONFIG_CACHE.clear()

    cfg.save_config({"model": {"default": "test-model"}})
    config_path = tmp_path / "config.yaml"

    # Simulate a legitimate hand edit: valid YAML, new content.
    config_path.write_text("model:\n  default: hand-edited\n", encoding="utf-8")

    loaded = cfg.load_config()
    # The edit is honored (user-editable file, not a hard failure)...
    assert loaded["model"]["default"] == "hand-edited"
    # ...and the sidecar is re-armed to the new content.
    assert state_hash_path(config_path).read_text(encoding="utf-8").strip() == (
        sha256_file(config_path)
    )


def test_config_raw_read_warns_and_rearms(tmp_path, monkeypatch):
    from xavani_cli import config as cfg

    monkeypatch.setenv("XAVANI_HOME", str(tmp_path))
    cfg._LOAD_CONFIG_CACHE.clear()
    cfg._RAW_CONFIG_CACHE.clear()

    cfg.save_config({"model": {"default": "test-model"}})
    config_path = tmp_path / "config.yaml"
    config_path.write_text("model:\n  default: raw-edit\n", encoding="utf-8")

    raw = cfg.read_raw_config()
    assert raw["model"]["default"] == "raw-edit"
    assert state_hash_path(config_path).read_text(encoding="utf-8").strip() == (
        sha256_file(config_path)
    )


def test_config_set_value_refreshes_sidecar(tmp_path, monkeypatch):
    from xavani_cli import config as cfg

    monkeypatch.setenv("XAVANI_HOME", str(tmp_path))
    cfg._LOAD_CONFIG_CACHE.clear()
    cfg._RAW_CONFIG_CACHE.clear()

    cfg.set_config_value("model.default", "set-via-cli")
    config_path = tmp_path / "config.yaml"
    assert config_path.exists()
    assert state_hash_path(config_path).read_text(encoding="utf-8").strip() == (
        sha256_file(config_path)
    )
