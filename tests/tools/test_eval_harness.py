# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate — Open source. Private. Local.

"""Tests for tools/eval_harness_tool.py — eval create/add/run/list/show/delete."""

import json
from unittest.mock import patch

import pytest

from tools.eval_harness_tool import (
    eval_create,
    eval_add,
    eval_run,
    eval_list,
    eval_show,
    eval_delete,
    _handle_eval_harness,
)

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _use_tmp_evals(tmp_path):
    """Redirect eval storage to tmp_path."""
    with patch("tools.eval_harness_tool._eval_dir", return_value=tmp_path):
        yield tmp_path


class TestEvalCreate:
    def test_create(self):
        result = json.loads(eval_create("test-eval", "A test eval"))
        assert result["ok"] is True
        assert "path" in result

    def test_create_duplicate(self):
        eval_create("test-eval")
        result = json.loads(eval_create("test-eval"))
        assert "error" in result


class TestEvalAdd:
    def test_add_case(self):
        eval_create("test-eval")
        result = json.loads(eval_add("test-eval", "case1", "hello", expected="HELLO"))
        assert result["ok"] is True

    def test_add_duplicate_case(self):
        eval_create("test-eval")
        eval_add("test-eval", "case1", "hello")
        result = json.loads(eval_add("test-eval", "case1", "hello"))
        assert "error" in result

    def test_add_to_nonexistent_eval(self):
        result = json.loads(eval_add("nope", "case1", "hello"))
        assert "error" in result


class TestEvalRun:
    def test_run_with_handler(self):
        """Run with a handler function reports pass/fail."""
        eval_create("test-eval")
        eval_add("test-eval", "c1", "hello", expected="HELLO")
        eval_add("test-eval", "c2", "world", expected="WORLD")

        def handler(input_text):
            return input_text.upper()

        result = json.loads(eval_run("test-eval", handler=handler))
        assert result["total"] == 2
        assert result["passed"] == 2
        assert result["pass_rate"] == "100.0%"

    def test_run_without_handler(self):
        """Run without handler returns cases for manual eval."""
        eval_create("test-eval")
        eval_add("test-eval", "c1", "hello")
        result = json.loads(eval_run("test-eval"))
        assert result["case_count"] == 1

    def test_run_partial_pass(self):
        """Handler that only matches one case."""
        eval_create("test-eval")
        eval_add("test-eval", "c1", "hello", expected="HELLO")
        eval_add("test-eval", "c2", "world", expected="XYZ")

        def handler(input_text):
            return input_text.upper()

        result = json.loads(eval_run("test-eval", handler=handler))
        assert result["passed"] == 1
        assert result["failed"] == 1

    def test_run_nonexistent_eval(self):
        result = json.loads(eval_run("nope"))
        assert "error" in result


class TestEvalList:
    def test_list_empty(self):
        result = json.loads(eval_list())
        assert result["evals"] == []

    def test_list_after_create(self):
        eval_create("eval-a")
        eval_create("eval-b")
        result = json.loads(eval_list())
        names = [e["name"] for e in result["evals"]]
        assert "eval-a" in names
        assert "eval-b" in names


class TestEvalShow:
    def test_show(self):
        eval_create("test-eval", "description here")
        eval_add("test-eval", "c1", "input")
        result = json.loads(eval_show("test-eval"))
        assert result["name"] == "test-eval"
        assert result["description"] == "description here"
        assert len(result["cases"]) == 1

    def test_show_nonexistent(self):
        result = json.loads(eval_show("nope"))
        assert "error" in result


class TestEvalDelete:
    def test_delete(self):
        eval_create("test-eval")
        result = json.loads(eval_delete("test-eval"))
        assert result["ok"] is True
        # Verify it's gone
        result = json.loads(eval_show("test-eval"))
        assert "error" in result


class TestEvalHandler:
    def test_handler_create(self):
        output = _handle_eval_harness({"action": "create", "name": "h-eval"})
        assert json.loads(output)["ok"] is True

    def test_handler_list(self):
        eval_create("h-eval")
        output = _handle_eval_harness({"action": "list"})
        assert "h-eval" in output

    def test_handler_unknown_action(self):
        output = _handle_eval_harness({"action": "invalid"})
        assert "error" in output
