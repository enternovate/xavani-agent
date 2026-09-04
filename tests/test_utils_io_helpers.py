"""Tests for utils IO helpers ported from Hermes."""

from utils import _preserve_file_owner, atomic_write_text, fast_safe_load


def test_fast_safe_load_parses_yaml_string():
    assert fast_safe_load("a: 1\nb:\n  - 2\n") == {"a": 1, "b": [2]}


def test_atomic_write_text_round_trips_content(tmp_path):
    target = tmp_path / "note.txt"
    atomic_write_text(target, "hello xavani")
    assert target.read_text(encoding="utf-8") == "hello xavani"


def test_preserve_file_owner_returns_tuple_or_none(tmp_path):
    target = tmp_path / "owned.txt"
    target.write_text("x", encoding="utf-8")
    result = _preserve_file_owner(target)
    assert result is None or (isinstance(result, tuple) and len(result) == 2)
