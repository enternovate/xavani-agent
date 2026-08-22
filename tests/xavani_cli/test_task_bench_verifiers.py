# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for extended bench verifiers (jsonschema, pytest, exit_code)."""

import pytest

from scripts.task_bench.run_bench import BenchError, parse_verifier


def test_jsonschema_verifier_passes_valid_object():
    check = parse_verifier(
        'jsonschema:{"type":"object","required":["total"],'
        '"properties":{"total":{"type":"number"}}}',
        "t1",
    )
    assert check('{"total": 43.20}') is True


def test_jsonschema_verifier_fails_invalid_or_non_json():
    check = parse_verifier(
        'jsonschema:{"type":"object","required":["total"]}', "t2"
    )
    assert check("no json here") is False
    assert check('{"wrong": true}') is False


def test_exit_code_verifier_matches_expected_code():
    check = parse_verifier("exit_code:0:python3 -c \"import sys; sys.exit(0)\"", "t3")
    assert check("anything") is True
    failing = parse_verifier("exit_code:3:python3 -c \"import sys; sys.exit(3)\"", "t4")
    assert failing("response") is True


def test_exit_code_verifier_rejects_malformed_payload():
    with pytest.raises(BenchError):
        parse_verifier("exit_code:0", "t5")
    with pytest.raises(BenchError):
        parse_verifier("exit_code:x:cat", "t6")


def test_pytest_verifier_runs_node(tmp_path):
    node_file = tmp_path / "test_bench_probe.py"
    node_file.write_text(
        "import os\n"
        "def test_response():\n"
        "    assert open(os.environ['BENCH_RESPONSE_FILE']).read() == 'good'\n",
        encoding="utf-8",
    )
    check = parse_verifier(f"pytest:{node_file}", "t7")
    assert check("good") is True
    assert check("bad") is False


def test_unknown_verifier_kind_still_rejected():
    with pytest.raises(BenchError):
        parse_verifier("magic:stuff", "t8")
