# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for failure root-cause labeling (A19) + seed capture (A14).

The hooks in tests/conftest.py categorize every test failure (assertion,
timeout, attribute, import, race, other) and append a record with the
nondeterminism sources (random state, hash seed, env, cwd) to
tests/flakiness.json.  These tests exercise the pure functions directly so
the bookkeeping is verified without deliberately failing real tests.
"""

import json
import random
from types import SimpleNamespace

from tests.conftest import (
    append_flakiness_record,
    build_failure_record,
    categorize_failure,
)


def test_categorize_failure_maps_exception_types():
    assert categorize_failure(AssertionError("x != y")) == "assertion_error"
    assert categorize_failure(TimeoutError("hung")) == "timeout"
    assert categorize_failure(AttributeError("no attr")) == "attribute_error"
    assert categorize_failure(ImportError("no module")) == "import_error"
    assert categorize_failure(ModuleNotFoundError("missing")) == "import_error"
    assert categorize_failure(ValueError("boom")) == "other"


def test_categorize_failure_uses_message_signatures():
    assert categorize_failure(ValueError("request timeout exceeded")) == "timeout"
    assert categorize_failure(RuntimeError("race condition detected")) == "race"
    assert categorize_failure(ConnectionResetError("peer reset")) == "race"
    assert categorize_failure(BrokenPipeError("pipe")) == "race"
    # Type match wins over a coincidental message match.
    assert categorize_failure(AssertionError("timeout in payload")) == "assertion_error"


def test_build_failure_record_captures_seed_and_environment():
    item = SimpleNamespace(nodeid="tests/test_demo.py::test_thing")
    exc = AssertionError("values differ")
    record = build_failure_record(item, exc, "assertion_error", "Traceback...")

    assert record["test_id"] == "tests/test_demo.py::test_thing"
    assert record["category"] == "assertion_error"
    assert record["label"] == "root_cause=assertion_error"
    assert record["exception_type"] == "AssertionError"
    assert record["traceback"] == "Traceback..."

    seed = record["seed_capture"]
    # repr(random.getstate()) is a long tuple of ints — non-empty and
    # substantial enough to replay the exact generator position.
    assert len(seed["random_state"]) > 10
    assert seed["cwd"]
    assert isinstance(seed["env"], dict)
    # Only behavioural vars are captured — never secret-shaped ones.
    assert not any("KEY" in k or "TOKEN" in k for k in seed["env"])


def test_append_flakiness_record_creates_and_appends(tmp_path):
    target = tmp_path / "flakiness.json"
    record = {"test_id": "t1", "category": "other"}
    append_flakiness_record(record, path=target)
    assert target.exists()
    assert json.loads(target.read_text(encoding="utf-8")) == [record]

    second = {"test_id": "t2", "category": "timeout"}
    append_flakiness_record(second, path=target)
    records = json.loads(target.read_text(encoding="utf-8"))
    assert records == [record, second]


def test_append_flakiness_record_recovers_from_corrupt_file(tmp_path):
    target = tmp_path / "flakiness.json"
    target.write_text("{not json", encoding="utf-8")
    append_flakiness_record({"test_id": "t1"}, path=target)
    assert json.loads(target.read_text(encoding="utf-8")) == [{"test_id": "t1"}]


def test_seed_capture_reflects_live_random_state():
    random.seed(12345)
    state_before = repr(random.getstate())
    random.random()  # advance the generator
    item = SimpleNamespace(nodeid="t")
    record = build_failure_record(item, ValueError("x"), "other", "")
    assert record["seed_capture"]["random_state"] != state_before
