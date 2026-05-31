# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Eval Harness Tool — Define, run, and report evaluation cases.

Encodes the principle "build the eval first." Allows the agent to define
eval cases (input -> expected output or assertion), run them, and report
pass rates. Designed for use before and after code changes to verify
behaviour is preserved or improved.

Eval cases are stored as JSON files under ``~/.xavani/evals/``. Each eval
file contains a list of cases with:
  * ``id`` — unique case identifier
  * ``input`` — the input to test
  * ``expected`` — the expected output (for exact/contains matching)
  * ``assertion`` — optional Python expression for custom checks
  * ``tags`` — optional labels for filtering

Actions:
  create  — Create a new eval set
  add     — Add a case to an eval set
  run     — Execute all cases in an eval set against a handler function
  list    — List available eval sets
  show    — Show cases in an eval set
  delete  — Remove an eval set
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import json as _json

# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------


def _eval_dir() -> Path:
    """Return the eval storage directory."""
    from xavani_constants import get_xavani_home
    d = get_xavani_home() / "evals"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _eval_path(name: str) -> Path:
    """Return the path to an eval set file."""
    safe_name = name.replace("/", "_").replace("\\", "_").replace("..", "_")
    return _eval_dir() / f"{safe_name}.json"


def _load_eval(name: str) -> Optional[Dict[str, Any]]:
    """Load an eval set from disk."""
    path = _eval_path(name)
    if not path.exists():
        return None
    try:
        return _json.loads(path.read_text(encoding="utf-8"))
    except (_json.JSONDecodeError, OSError):
        return None


def _save_eval(name: str, data: Dict[str, Any]) -> None:
    """Save an eval set to disk."""
    path = _eval_path(name)
    path.write_text(_json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


def eval_create(name: str, description: str = "") -> str:
    """Create a new eval set."""
    if _load_eval(name):
        return _json.dumps({"error": f"Eval set '{name}' already exists."})

    data = {
        "name": name,
        "description": description,
        "created_at": time.time(),
        "cases": [],
    }
    _save_eval(name, data)
    return _json.dumps({"ok": True, "message": f"Eval set '{name}' created.", "path": str(_eval_path(name))})


def eval_add(
    name: str,
    case_id: str,
    input_text: str,
    expected: str = "",
    assertion: str = "",
    tags: Optional[List[str]] = None,
) -> str:
    """Add a case to an eval set."""
    data = _load_eval(name)
    if not data:
        return _json.dumps({"error": f"Eval set '{name}' not found."})

    # Check for duplicate ID
    for case in data["cases"]:
        if case["id"] == case_id:
            return _json.dumps({"error": f"Case '{case_id}' already exists in '{name}'."})

    case = {
        "id": case_id,
        "input": input_text,
        "expected": expected,
        "assertion": assertion,
        "tags": tags or [],
    }
    data["cases"].append(case)
    _save_eval(name, data)
    return _json.dumps({"ok": True, "message": f"Case '{case_id}' added to '{name}'."})


def eval_run(
    name: str,
    handler: Optional[Callable[[str], str]] = None,
    handler_name: str = "default",
    tags: Optional[List[str]] = None,
) -> str:
    """Run all cases in an eval set.

    If no handler is provided, returns the cases for manual evaluation.
    If a handler is provided, runs each case's input through it and checks
    the output against expected/assertion.
    """
    data = _load_eval(name)
    if not data:
        return _json.dumps({"error": f"Eval set '{name}' not found."})

    cases = data["cases"]
    if tags:
        cases = [c for c in cases if any(t in c.get("tags", []) for t in tags)]

    if not cases:
        return _json.dumps({"error": f"No cases found in '{name}'" + (f" matching tags {tags}" if tags else "") + "."})

    if handler is None:
        # Return cases for manual evaluation
        return _json.dumps({
            "eval_set": name,
            "case_count": len(cases),
            "cases": cases,
            "note": "No handler provided. Pass a handler function to run automatically.",
        }, indent=2)

    results = []
    passed = 0
    failed = 0
    errors = 0

    for case in cases:
        case_id = case["id"]
        try:
            output = handler(case["input"])
            result = {"id": case_id, "output": output, "status": "unknown"}

            if case.get("assertion"):
                # Custom assertion
                try:
                    assertion_result = eval(case["assertion"], {"output": output, "input": case["input"]})
                    result["status"] = "pass" if assertion_result else "fail"
                except Exception as exc:
                    result["status"] = "error"
                    result["assertion_error"] = str(exc)
            elif case.get("expected"):
                # Exact or contains match
                if case["expected"] in output:
                    result["status"] = "pass"
                else:
                    result["status"] = "fail"
                    result["expected"] = case["expected"]
            else:
                # No assertion or expected — just record the output
                result["status"] = "pass"

            if result["status"] == "pass":
                passed += 1
            elif result["status"] == "fail":
                failed += 1
            else:
                errors += 1

        except Exception as exc:
            result = {"id": case_id, "status": "error", "error": str(exc)}
            errors += 1

        results.append(result)

    total = len(results)
    pass_rate = (passed / total * 100) if total > 0 else 0

    return _json.dumps({
        "eval_set": name,
        "handler": handler_name,
        "total": total,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "pass_rate": f"{pass_rate:.1f}%",
        "results": results,
    }, indent=2)


def eval_list() -> str:
    """List available eval sets."""
    d = _eval_dir()
    evals = []
    for path in sorted(d.glob("*.json")):
        try:
            data = _json.loads(path.read_text(encoding="utf-8"))
            evals.append({
                "name": data.get("name", path.stem),
                "description": data.get("description", ""),
                "case_count": len(data.get("cases", [])),
                "created_at": data.get("created_at"),
            })
        except Exception:
            continue
    return _json.dumps({"evals": evals}, indent=2)


def eval_show(name: str) -> str:
    """Show cases in an eval set."""
    data = _load_eval(name)
    if not data:
        return _json.dumps({"error": f"Eval set '{name}' not found."})
    return _json.dumps(data, indent=2)


def eval_delete(name: str) -> str:
    """Remove an eval set."""
    path = _eval_path(name)
    if not path.exists():
        return _json.dumps({"error": f"Eval set '{name}' not found."})
    path.unlink()
    return _json.dumps({"ok": True, "message": f"Eval set '{name}' deleted."})


# ---------------------------------------------------------------------------
# Tool handler
# ---------------------------------------------------------------------------


def _handle_eval_harness(args: Dict[str, Any]) -> str:
    """Tool handler for the eval harness."""
    action = args.get("action", "")

    if action == "create":
        return eval_create(
            name=args.get("name", ""),
            description=args.get("description", ""),
        )
    elif action == "add":
        return eval_add(
            name=args.get("name", ""),
            case_id=args.get("case_id", ""),
            input_text=args.get("input", ""),
            expected=args.get("expected", ""),
            assertion=args.get("assertion", ""),
            tags=args.get("tags"),
        )
    elif action == "run":
        return eval_run(
            name=args.get("name", ""),
            tags=args.get("tags"),
        )
    elif action == "list":
        return eval_list()
    elif action == "show":
        return eval_show(name=args.get("name", ""))
    elif action == "delete":
        return eval_delete(name=args.get("name", ""))
    else:
        return _json.dumps({"error": f"Unknown action: {action}. Use: create, add, run, list, show, delete."})


# ---------------------------------------------------------------------------
# Tool schema
# ---------------------------------------------------------------------------

EVAL_HARNESS_SCHEMA: Dict[str, Any] = {
    "name": "eval_harness",
    "description": (
        "Define, run, and report evaluation cases. Build the eval first — "
        "define what success looks like before writing the code. "
        "Actions: create (new eval set), add (add a case), run (execute cases), "
        "list (show eval sets), show (show cases), delete (remove eval set)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "add", "run", "list", "show", "delete"],
                "description": "The action to perform.",
            },
            "name": {
                "type": "string",
                "description": "Eval set name.",
            },
            "description": {
                "type": "string",
                "description": "Description for the eval set (create action).",
            },
            "case_id": {
                "type": "string",
                "description": "Unique case identifier (add action).",
            },
            "input": {
                "type": "string",
                "description": "Input text for the case (add action).",
            },
            "expected": {
                "type": "string",
                "description": "Expected output substring for matching (add action).",
            },
            "assertion": {
                "type": "string",
                "description": "Python expression for custom assertion. 'output' and 'input' are available (add action).",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Tags for filtering cases (add/run action).",
            },
        },
        "required": ["action"],
    },
}


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

from tools.registry import registry  # noqa: E402

registry.register(
    name="eval_harness",
    toolset="skills",
    schema=EVAL_HARNESS_SCHEMA,
    handler=_handle_eval_harness,
    description="Define, run, and report evaluation cases. Build the eval first.",
    emoji="📊",
)
