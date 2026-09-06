import sqlite3


def test_transient_classifier():
    from xavani_state import is_transient_sqlite_error

    assert is_transient_sqlite_error(sqlite3.OperationalError("database is locked")) is True
    assert is_transient_sqlite_error(ValueError("nope")) is False


def test_persistence_buckets():
    from xavani_state import classify_persistence_error

    assert classify_persistence_error("database is locked") == "locked"
    assert classify_persistence_error(None) == "unknown"


def test_claim_repair_single_shot(tmp_path):
    from xavani_state import _claim_repair_attempt

    target = tmp_path / "state.db"
    assert _claim_repair_attempt(target) is True
    assert _claim_repair_attempt(target) is False


def test_error_classes_import():
    from xavani_state import (
        CompressionSessionBusyError,
        CompressionSessionClosedError,
        SessionTurnLeaseLostError,
        StateDbCorruptError,
        StateDbReplacedError,
    )

    assert issubclass(StateDbCorruptError, sqlite3.DatabaseError)
    assert issubclass(StateDbReplacedError, RuntimeError)
    assert issubclass(SessionTurnLeaseLostError, RuntimeError)
    assert issubclass(CompressionSessionBusyError, RuntimeError)
    assert issubclass(CompressionSessionClosedError, RuntimeError)
