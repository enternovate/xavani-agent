#!/usr/bin/env python3

# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Task-cost benchmark harness (smallest cost per successful task).

Runs each task in a JSON tasks file through one AIAgent conversation turn
and measures wall seconds, token usage, and estimated cost per task, plus
a verifier-derived success flag. Aggregates report median/p90 wall time,
mean tokens, total cost, cost per successful task, and success rate —
the two optimization targets are cost-per-successful-task and median wall
time (< 100s).

Tasks file format::

    [
      {"id": "task-1", "prompt": "...", "verifier": "contains:expected"},
      {"id": "task-2", "prompt": "...", "verifier": "regex:pattern"},
      {"id": "task-3", "prompt": "...", "verifier": "contains:x",
       "faux_response": "scripted reply used only in --faux mode"}
    ]

``--faux`` replays scripted responses through the real agent loop via the
``tests.harness.faux_provider`` transport seam (no network, no API keys),
so CI can exercise the harness deterministically.

CLI: ``python3 -m scripts.task_bench.run_bench [--faux] [--out results.json]``
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from contextlib import ExitStack
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from unittest.mock import patch

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

DEFAULT_TASKS_PATH = Path(__file__).resolve().parent / "tasks" / "baseline_tasks.json"
_VERIFIER_RE = re.compile(r"^(contains|regex):(.+)$", re.DOTALL)


class BenchError(ValueError):
    pass


def load_tasks(path: Path) -> List[Dict[str, Any]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise BenchError(f"cannot read tasks file {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise BenchError(f"tasks file {path} is not valid JSON: {exc}") from exc
    if not isinstance(raw, list) or not raw:
        raise BenchError(f"tasks file {path} must be a non-empty JSON list")
    seen_ids = set()
    for index, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise BenchError(f"task #{index} in {path} must be an object")
        task_id = entry.get("id")
        if not isinstance(task_id, str) or not task_id.strip():
            raise BenchError(f"task #{index} in {path} needs a non-empty string 'id'")
        if task_id in seen_ids:
            raise BenchError(f"duplicate task id {task_id!r} in {path}")
        seen_ids.add(task_id)
        prompt = entry.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise BenchError(f"task {task_id!r} needs a non-empty string 'prompt'")
        verifier = entry.get("verifier")
        parse_verifier(verifier if isinstance(verifier, str) else None, task_id)
    return raw


def parse_verifier(verifier: Optional[str], task_id: str = "?") -> Callable[[str], bool]:
    if not isinstance(verifier, str):
        raise BenchError(f"task {task_id!r} needs a string 'verifier'")
    match = _VERIFIER_RE.match(verifier)
    if not match:
        raise BenchError(
            f"task {task_id!r} verifier must start with 'contains:' or 'regex:', got {verifier!r}"
        )
    kind, payload = match.group(1), match.group(2)
    if kind == "contains":
        needle = payload
        return lambda response: needle in response
    try:
        pattern = re.compile(payload)
    except re.error as exc:
        raise BenchError(f"task {task_id!r} has invalid regex verifier {payload!r}: {exc}") from exc
    return lambda response: pattern.search(response) is not None


def _faux_response_for(task: Dict[str, Any]) -> str:
    scripted = task.get("faux_response")
    if isinstance(scripted, str) and scripted:
        return scripted
    _, _, payload = task["verifier"].partition(":")
    return payload


def _make_tool_defs(*names: str) -> list:
    return [
        {
            "type": "function",
            "function": {
                "name": n,
                "description": f"{n} tool",
                "parameters": {"type": "object", "properties": {}},
            },
        }
        for n in names
    ]


def run_task(
    task: Dict[str, Any],
    *,
    provider: Optional[str] = None,
    model: str = "",
    faux: bool = False,
) -> Dict[str, Any]:
    from run_agent import AIAgent

    session = None
    stack = ExitStack()
    try:
        if faux:
            from tests.harness.faux_provider import ScriptedSession

            session = ScriptedSession()
            session.text(_faux_response_for(task), model=model or "faux-model")
            stack.enter_context(
                patch(
                    "run_agent.get_tool_definitions",
                    return_value=_make_tool_defs("skills_list"),
                )
            )
            stack.enter_context(
                patch("run_agent.check_toolset_requirements", return_value={})
            )
            stack.enter_context(patch("run_agent.OpenAI", session.client_factory()))
            init_kwargs: Dict[str, Any] = {
                "api_key": "bench-faux-key",
                "base_url": "https://openrouter.ai/api/v1",
                "model": model or "faux-model",
                "quiet_mode": True,
                "skip_context_files": True,
                "skip_memory": True,
            }
            if provider:
                init_kwargs["provider"] = provider
            agent = AIAgent(**init_kwargs)
            agent._persist_session = lambda *a, **k: None
            agent._save_trajectory = lambda *a, **k: None
            agent._save_session_log = lambda *a, **k: None
            agent.suppress_status_output = True
            # Faux chunks carry no usage block; route to the non-streaming
            # transport so the scripted completion's usage reaches
            # record_session_usage() and the cost estimator.
            agent._disable_streaming = True
        else:
            init_kwargs = {
                "model": model,
                "quiet_mode": True,
                "skip_context_files": True,
                "skip_memory": True,
            }
            if provider:
                init_kwargs["provider"] = provider
            agent = AIAgent(**init_kwargs)

        error: Optional[str] = None
        response = ""
        start = time.perf_counter()
        try:
            result = agent.run_conversation(task["prompt"])
            response = result.get("final_response") or ""
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
        wall_seconds = time.perf_counter() - start

        success = error is None and parse_verifier(task["verifier"], task["id"])(response)
        return {
            "id": task["id"],
            "success": bool(success),
            "wall_seconds": round(wall_seconds, 4),
            "total_tokens": int(getattr(agent, "session_total_tokens", 0) or 0),
            "prompt_tokens": int(getattr(agent, "session_prompt_tokens", 0) or 0),
            "completion_tokens": int(getattr(agent, "session_completion_tokens", 0) or 0),
            "estimated_cost_usd": float(
                getattr(agent, "session_estimated_cost_usd", 0.0) or 0.0
            ),
            "api_calls": int(getattr(agent, "session_api_calls", 0) or 0),
            "response_chars": len(response),
            "error": error,
        }
    finally:
        stack.close()


def percentile(values: List[float], q: float) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * q
    low = math.floor(pos)
    high = math.ceil(pos)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (pos - low)


def summarize_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    walls = [r["wall_seconds"] for r in results]
    tokens = [r["total_tokens"] for r in results]
    total_cost = sum(r["estimated_cost_usd"] for r in results)
    successful = [r for r in results if r["success"]]
    return {
        "task_count": len(results),
        "success_count": len(successful),
        "success_rate": (len(successful) / len(results)) if results else 0.0,
        "median_wall_seconds": percentile(walls, 0.5),
        "p90_wall_seconds": percentile(walls, 0.9),
        "mean_total_tokens": (sum(tokens) / len(tokens)) if tokens else 0.0,
        "total_cost_usd": total_cost,
        "cost_per_successful_task_usd": (
            total_cost / len(successful) if successful else None
        ),
    }


def render_summary(results: List[Dict[str, Any]], summary: Dict[str, Any]) -> str:
    lines = [
        f"{'task':<32} {'result':<6} {'wall_s':>9} {'tokens':>8} {'cost_usd':>12}"
    ]
    for r in results:
        lines.append(
            f"{r['id']:<32} {'pass' if r['success'] else 'FAIL':<6} "
            f"{r['wall_seconds']:>9.4f} {r['total_tokens']:>8} "
            f"{r['estimated_cost_usd']:>12.6f}"
        )
    lines.append("")
    lines.append(
        f"tasks={summary['task_count']}  "
        f"success={summary['success_count']}/{summary['task_count']} "
        f"({summary['success_rate'] * 100:.1f}%)"
    )
    lines.append(
        f"median_wall_s={summary['median_wall_seconds']:.4f}  "
        f"p90_wall_s={summary['p90_wall_seconds']:.4f}"
    )
    lines.append(
        f"mean_total_tokens={summary['mean_total_tokens']:.1f}  "
        f"total_cost_usd={summary['total_cost_usd']:.6f}"
    )
    per_success = summary["cost_per_successful_task_usd"]
    per_success_str = f"{per_success:.6f}" if per_success is not None else "n/a"
    lines.append(f"cost_per_successful_task_usd={per_success_str}")
    return "\n".join(lines)


def run_benchmark(
    tasks: List[Dict[str, Any]],
    *,
    provider: Optional[str] = None,
    model: str = "",
    faux: bool = False,
) -> Dict[str, Any]:
    results = [
        run_task(task, provider=provider, model=model, faux=faux) for task in tasks
    ]
    return {"results": results, "summary": summarize_results(results)}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="task_bench",
        description="Benchmark wall time, tokens, cost, and success rate per task.",
    )
    parser.add_argument(
        "tasks_file",
        nargs="?",
        default=None,
        help=f"JSON tasks file (default: {DEFAULT_TASKS_PATH})",
    )
    parser.add_argument("--out", default=None, help="write full JSON results here")
    parser.add_argument("--provider", default=None, help="provider passthrough")
    parser.add_argument("--model", default="", help="model passthrough")
    parser.add_argument(
        "--faux",
        action="store_true",
        help="scripted offline provider via the faux transport seam (no network)",
    )
    args = parser.parse_args(argv)

    tasks_path = Path(args.tasks_file) if args.tasks_file else DEFAULT_TASKS_PATH
    try:
        tasks = load_tasks(tasks_path)
    except BenchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    bench = run_benchmark(tasks, provider=args.provider, model=args.model, faux=args.faux)
    payload = {
        "tasks_file": str(tasks_path),
        "mode": "faux" if args.faux else "live",
        "provider": args.provider,
        "model": args.model or None,
        **bench,
    }

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(f"results written to {out_path}")
    print(render_summary(bench["results"], bench["summary"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
