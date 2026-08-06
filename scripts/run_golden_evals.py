#!/usr/bin/env python3
# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Eval-gate runner.

Runs the golden eval set through a deterministic handler and exits
non-zero when any case fails. CI (eval-gate.yml) invokes this whenever
steer paths (run_agent.py, conversation_loop.py, agent_init.py, cli.py)
change, so a behaviour regression blocks the merge.

Usage:
    python3 scripts/run_golden_evals.py [--evals PATH] [--handler MODULE:FUNC]
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional

ROOT = Path(__file__).resolve().parent.parent
GOLDEN_PATH = ROOT / "tests" / "fixtures" / "golden-evals.json"


def load_golden_evals(path: Path = GOLDEN_PATH) -> Dict[str, Any]:
    """Load the golden eval set JSON."""
    if not path.exists():
        sys.exit(f"golden evals not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.exit(f"golden evals JSON invalid: {exc}")
    if not isinstance(data, dict) or "cases" not in data:
        sys.exit("golden evals must be {name, cases: [...]}")
    return data


def resolve_handler(spec: str) -> Callable[[str], str]:
    """Resolve ``module:function`` to a callable."""
    module_name, _, func_name = spec.partition(":")
    if not func_name:
        sys.exit("--handler must be MODULE:FUNC")
    if ROOT not in [str(p) for p in sys.path]:
        sys.path.insert(0, str(ROOT))
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        sys.exit(f"cannot import handler module {module_name}: {exc}")
    handler = getattr(module, func_name, None)
    if not callable(handler):
        sys.exit(f"{module_name}.{func_name} is not callable")
    return handler  # type: ignore[return-value]


def run_golden_evals(evals_path: Path, handler: Callable[[str], str]) -> Dict[str, Any]:
    """Run every golden case through the handler; return the report."""
    data = load_golden_evals(evals_path)
    cases = data["cases"]
    results = []
    passed = 0
    failed = 0
    for case in cases:
        case_id = case.get("id", "<no-id>")
        expected = case.get("expected", "")
        try:
            output = handler(case.get("input", ""))
        except Exception as exc:  # noqa: BLE001 — report, don't crash
            results.append({"id": case_id, "ok": False, "error": f"{type(exc).__name__}: {exc}"})
            failed += 1
            continue
        ok = expected in output
        results.append({"id": case_id, "ok": ok, "expected": expected, "got": output[:200]})
        if ok:
            passed += 1
        else:
            failed += 1
    return {"eval_set": data.get("name", "golden"), "passed": passed, "failed": failed, "results": results}


def main(argv: Optional[list[str]] = None) -> int:
    """CLI entry point; returns the process exit code."""
    parser = argparse.ArgumentParser(description="Run the golden eval gate.")
    parser.add_argument("--evals", type=Path, default=GOLDEN_PATH, help="path to golden evals JSON")
    parser.add_argument("--handler", default="tools.eval_harness_tool:eval_run", help="MODULE:FUNC handler")
    args = parser.parse_args(argv)

    # Default handler: run each input through eval_run's default behaviour —
    # for the gate we want a deterministic pure handler, so a fixture module
    # must supply one. Require it explicitly when the default is not usable.
    handler = resolve_handler(args.handler)
    report = run_golden_evals(args.evals, handler)
    print(f"eval-gate {report['eval_set']}: {report['passed']} passed, {report['failed']} failed")
    for result in report["results"]:
        if not result["ok"]:
            print(f"  FAIL {result['id']}: expected={result.get('expected')!r} got={result.get('got')!r} error={result.get('error', '')}")
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
