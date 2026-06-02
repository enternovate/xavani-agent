# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the document reading tool (v0.4.0 U36)."""

from __future__ import annotations

import ast
import inspect
import json

import tools.document_tools as dt


def test_tool_is_registered():
    from tools.registry import registry

    assert registry.get_schema("read_document") is not None


def test_reads_plaintext(tmp_path):
    f = tmp_path / "note.txt"
    f.write_text("hello world\nsecond line", encoding="utf-8")
    out = dt.read_document(str(f))
    assert out["format"] == "txt"
    assert "hello world" in out["text"]
    assert out["chars"] == len("hello world\nsecond line")


def test_missing_file_returns_error():
    out = dt.read_document("/no/such/file.txt")
    assert "error" in out and "not a file" in out["error"]


def test_unsupported_extension_returns_error(tmp_path):
    f = tmp_path / "thing.xyz"
    f.write_text("data", encoding="utf-8")
    out = dt.read_document(str(f))
    assert "error" in out and "unsupported" in out["error"]


def test_max_chars_truncates(tmp_path):
    f = tmp_path / "big.txt"
    f.write_text("x" * 100, encoding="utf-8")
    out = dt.read_document(str(f), max_chars=10)
    assert out["chars"] == 10
    assert out.get("truncated") is True


def test_handler_returns_json(tmp_path):
    f = tmp_path / "h.md"
    f.write_text("# title", encoding="utf-8")
    raw = dt._handle_read_document({"path": str(f)})
    parsed = json.loads(raw)
    assert parsed["format"] == "md"
    assert "title" in parsed["text"]


def test_handler_requires_path():
    parsed = json.loads(dt._handle_read_document({}))
    assert "error" in parsed


def test_document_tools_is_llm_free():
    tree = ast.parse(inspect.getsource(dt))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert not (imported & {"openai", "anthropic", "litellm", "cohere", "mistralai", "groq"})
