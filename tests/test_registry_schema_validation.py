# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""S3-2 (backlog D78): tool-argument schema validation at registry dispatch.

dispatch() must reject unknown parameters (strict schemas), missing required
fields, and primitive type mismatches with a tool_error-style string BEFORE
the handler runs; opt-out tools (schema_validation=False or the documented
name-based opt-out list) bypass validation entirely.
"""

import json

from tools.registry import ToolRegistry, registry


def _schema(name="validated", **params):
    parameters = {"type": "object", "properties": {}}
    parameters.update(params)
    return {"name": name, "description": f"A {name}", "parameters": parameters}


def _make_registry(schema=None, handler=None, **reg_kwargs):
    reg = ToolRegistry()
    calls = {"n": 0}

    def default_handler(args, **kwargs):
        calls["n"] += 1
        return json.dumps({"ok": True, "args": args})

    reg.register(
        name="validated",
        toolset="test",
        schema=schema if schema is not None else _schema(),
        handler=handler or default_handler,
        **reg_kwargs,
    )
    return reg, calls


def test_unknown_parameter_rejected():
    schema = _schema(
        additionalProperties=False,
        properties={"known": {"type": "string"}},
    )
    reg, calls = _make_registry(schema=schema)
    result = json.loads(reg.dispatch("validated", {"known": "x", "bogus": 1}))
    assert "error" in result
    assert "Unknown parameter" in result["error"]
    assert "bogus" in result["error"]
    assert calls["n"] == 0


def test_missing_required_rejected():
    schema = _schema(properties={"name": {"type": "string"}}, required=["name"])
    reg, calls = _make_registry(schema=schema)
    result = json.loads(reg.dispatch("validated", {}))
    assert "error" in result
    assert "Missing required" in result["error"]
    assert "name" in result["error"]
    assert calls["n"] == 0


def test_type_mismatch_rejected():
    schema = _schema(
        properties={
            "count": {"type": "integer"},
            "flag": {"type": "boolean"},
            "label": {"type": "string"},
            "ratio": {"type": "number"},
        }
    )
    reg, calls = _make_registry(schema=schema)
    for bad in ({"count": "3"}, {"flag": "yes"}, {"label": 7}, {"ratio": "1.5"}):
        result = json.loads(reg.dispatch("validated", bad))
        assert "error" in result
        assert "must be" in result["error"]
    assert calls["n"] == 0
    ok = json.loads(
        reg.dispatch(
            "validated", {"count": 3, "flag": True, "label": "x", "ratio": 1.5}
        )
    )
    assert ok == {"ok": True, "args": {"count": 3, "flag": True, "label": "x", "ratio": 1.5}}
    assert calls["n"] == 1


def test_valid_call_invokes_handler():
    schema = _schema(properties={"name": {"type": "string"}}, required=["name"])
    reg, calls = _make_registry(schema=schema)
    result = json.loads(reg.dispatch("validated", {"name": "x"}))
    assert result == {"ok": True, "args": {"name": "x"}}
    assert calls["n"] == 1


def test_opt_out_flag_bypasses_validation():
    schema = _schema(
        additionalProperties=False,
        properties={"name": {"type": "string"}},
        required=["name"],
    )
    reg, calls = _make_registry(schema=schema, schema_validation=False)
    result = json.loads(reg.dispatch("validated", {"bogus": 1}))
    assert calls["n"] == 1
    assert "error" not in result


def test_real_registered_tool_still_dispatches():
    import tools.todo_tool  # noqa: F401  (registers "todo" on the singleton)

    entry = registry.get_entry("todo")
    assert entry is not None
    result = json.loads(registry.dispatch("todo", {}))
    assert "error" in result
    assert "TodoStore" in result["error"]  # handler ran; validation passed


def test_tool_call_meta_tool_opted_out():
    import tools.tool_call_tool  # noqa: F401  (registers "tool_call" on the singleton)

    entry = registry.get_entry("tool_call")
    assert entry is not None
    assert entry.validation_plan is None
