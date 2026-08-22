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
import os
import re
import subprocess
import sys
import tempfile
import time
from contextlib import ExitStack
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from unittest.mock import patch

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

DEFAULT_TASKS_PATH = Path(__file__).resolve().parent / "tasks" / "baseline_tasks.json"
RESULTS_DIR = Path(__file__).resolve().parent / "results"
_VERIFIER_RE = re.compile(
    r"^(contains|regex|jsonschema|pytest|exit_code|llm_judge):(.+)$", re.DOTALL
)
_DEFAULT_VERIFIER_TIMEOUT_S = 120


def _response_text(response: Any) -> str:
    """Extract plain text from a str, .content object, or OpenAI shape."""
    if isinstance(response, str):
        return response
    content = getattr(response, "content", None)
    if isinstance(content, str):
        return content
    choices = getattr(response, "choices", None)
    if choices:
        message = getattr(choices[0], "message", None)
        text = getattr(message, "content", None)
        if isinstance(text, str):
            return text
    return ""


def _verifier_llm_judge(payload: str, task_id: str) -> Callable[[str], bool]:
    """Judge a response against a rubric file of verifier lines.

    Default judge is deterministic: every ``contains:``/``regex:`` line in
    the rubric must pass. Set ``XAVANI_BENCH_JUDGE_MODEL`` to also require
    a model yes/no verdict through the auxiliary client.
    """
    rubric_path = Path(payload)
    if not rubric_path.is_file():
        raise BenchError(f"task {task_id!r} llm_judge rubric not found: {payload}")
    try:
        lines = [
            line.strip()
            for line in rubric_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
    except OSError as exc:
        raise BenchError(
            f"task {task_id!r} llm_judge rubric unreadable: {exc}"
        ) from exc
    if not lines:
        raise BenchError(f"task {task_id!r} llm_judge rubric has no verifier lines")
    checks = [parse_verifier(line, task_id) for line in lines]

    model_judge: Optional[Callable[[str], bool]] = None
    judge_model = os.getenv("XAVANI_BENCH_JUDGE_MODEL", "").strip()
    if judge_model:

        def _model_verdict(response: str, model: str = judge_model) -> bool:
            from agent.auxiliary_client import call_llm

            verdict = call_llm(
                provider=None,
                model=model,
                messages=[
                    {"role": "system", "content": (
                        "You are a strict grader. First reason briefly, then "
                        "end your reply with exactly YES or NO: does the "
                        "response satisfy the request?"
                    )},
                    {"role": "user", "content": response[:8000]},
                ],
                temperature=0.0,
                max_tokens=1000,
            )
            content = _response_text(verdict).strip()
            text = content
            if not text:
                choices = getattr(verdict, "choices", None)
                if choices:
                    message = choices[0].message
                    text = str(
                        getattr(message, "reasoning", None) or ""
                    ).strip()
            upper = text.upper()
            return upper.rstrip().endswith("YES") and " NO" not in upper[-8:]

        model_judge = _model_verdict

    def check(response: str) -> bool:
        if not all(check_(response) for check_ in checks):
            return False
        return model_judge(response) if model_judge else True

    return check


def _verifier_jsonschema(payload: str, task_id: str) -> Callable[[str], bool]:
    try:
        import jsonschema
    except ImportError as exc:
        raise BenchError(
            f"task {task_id!r} jsonschema verifier needs the jsonschema package"
        ) from exc
    try:
        schema = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise BenchError(
            f"task {task_id!r} has invalid JSON schema verifier: {exc}"
        ) from exc
    validator = jsonschema.Draft7Validator(schema)

    def check(response: str) -> bool:
        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            return False
        return not list(validator.iter_errors(data))

    return check


def _verifier_pytest(
    payload: str, task_id: str, timeout_s: float = _DEFAULT_VERIFIER_TIMEOUT_S
) -> Callable[[str], bool]:
    def check(response: str) -> bool:
        with tempfile.TemporaryDirectory() as td:
            node_file = Path(td) / "response.txt"
            node_file.write_text(response, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-m", "pytest", payload, "-q", "--no-header", "-x"],
                capture_output=True, text=True, timeout=timeout_s,
                env={**os.environ, "BENCH_RESPONSE_FILE": str(node_file)},
            )
            return result.returncode == 0

    return check


def _verifier_exit_code(
    payload: str, task_id: str, timeout_s: float = _DEFAULT_VERIFIER_TIMEOUT_S
) -> Callable[[str], bool]:
    expected_str, sep, command = payload.partition(":")
    if not sep or not command.strip():
        raise BenchError(
            f"task {task_id!r} exit_code verifier needs 'exit_code:<N>:<command>'; "
            "the response is piped to the command on stdin"
        )
    try:
        expected = int(expected_str)
    except ValueError as exc:
        raise BenchError(
            f"task {task_id!r} exit_code verifier needs an integer code, got {expected_str!r}"
        ) from exc

    def check(response: str) -> bool:
        result = subprocess.run(
            command, input=response, capture_output=True, text=True,
            timeout=timeout_s, shell=True,
        )
        return result.returncode == expected

    return check


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
        timeout = entry.get("timeout_seconds")
        if timeout is not None and (
            not isinstance(timeout, (int, float)) or timeout <= 0
        ):
            raise BenchError(
                f"task {task_id!r} timeout_seconds must be a positive number"
            )
    return raw


def parse_verifier(
    verifier: Optional[str],
    task_id: str = "?",
    timeout_s: float = _DEFAULT_VERIFIER_TIMEOUT_S,
) -> Callable[[str], bool]:
    if not isinstance(verifier, str):
        raise BenchError(f"task {task_id!r} needs a string 'verifier'")
    match = _VERIFIER_RE.match(verifier)
    if not match:
        raise BenchError(
            f"task {task_id!r} verifier must start with one of "
            "contains:, regex:, jsonschema:, pytest:, exit_code:, "
            f"llm_judge: — got {verifier!r}"
        )
    kind, payload = match.group(1), match.group(2)
    if kind == "jsonschema":
        return _verifier_jsonschema(payload, task_id)
    if kind == "pytest":
        return _verifier_pytest(payload, task_id, timeout_s=timeout_s)
    if kind == "exit_code":
        return _verifier_exit_code(payload, task_id, timeout_s=timeout_s)
    if kind == "llm_judge":
        return _verifier_llm_judge(payload, task_id)
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

        success = error is None and parse_verifier(
            task["verifier"],
            task["id"],
            timeout_s=float(task.get("timeout_seconds") or _DEFAULT_VERIFIER_TIMEOUT_S),
        )(response)
        return {
            "id": task["id"],
            "category": task.get("category", "general"),
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
    categories: Dict[str, List[float]] = {}
    for result in results:
        categories.setdefault(result.get("category", "general"), []).append(
            result["wall_seconds"]
        )
    return {
        "task_count": len(results),
        "success_count": len(successful),
        "success_rate": (len(successful) / len(results)) if results else 0.0,
        "median_wall_seconds": percentile(walls, 0.5),
        "p90_wall_seconds": percentile(walls, 0.9),
        "p95_wall_seconds": percentile(walls, 0.95),
        "per_category_median_wall_seconds": {
            cat: percentile(cat_walls, 0.5)
            for cat, cat_walls in sorted(categories.items())
        },
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
        f"p90_wall_s={summary['p90_wall_seconds']:.4f}  "
        f"p95_wall_s={summary['p95_wall_seconds']:.4f}"
    )
    per_category = summary.get("per_category_median_wall_seconds") or {}
    for cat, median in per_category.items():
        lines.append(f"  median[{cat}]={median:.4f}")
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
    runs: int = 1,
) -> Dict[str, Any]:
    """Run the suite ``runs`` times; flag tasks unstable across runs.

    With ``runs > 1`` a task is a flake when its success flag differs
    between runs; flakes are dropped from the returned results and
    listed under ``unstable_ids``.
    """
    all_results = [
        run_task(task, provider=provider, model=model, faux=faux) for task in tasks
    ]
    if runs <= 1:
        return {"results": all_results, "summary": summarize_results(all_results)}

    repeat_results = [
        run_task(task, provider=provider, model=model, faux=faux)
        for task in tasks
        for _ in range(runs - 1)
    ]
    merged: Dict[str, list] = {}
    for result in [*all_results, *repeat_results]:
        merged.setdefault(result["id"], []).append(result["success"])
    unstable_ids = sorted(
        task_id for task_id, successes in merged.items() if len(set(successes)) > 1
    )
    stable = [r for r in all_results if r["id"] not in set(unstable_ids)]
    return {
        "results": stable,
        "summary": summarize_results(stable),
        "unstable_ids": unstable_ids,
    }


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
    parser.add_argument(
        "--category",
        default=None,
        help="run only tasks whose category matches this string",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="run the suite N times and drop tasks unstable across runs (flake check)",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help=f"write results under {RESULTS_DIR} with a config fingerprint name",
    )
    args = parser.parse_args(argv)

    tasks_path = Path(args.tasks_file) if args.tasks_file else DEFAULT_TASKS_PATH
    try:
        tasks = load_tasks(tasks_path)
    except BenchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.category:
        tasks = [t for t in tasks if t.get("category") == args.category]
        if not tasks:
            print(f"error: no tasks in category {args.category!r}", file=sys.stderr)
            return 2

    bench = run_benchmark(
        tasks, provider=args.provider, model=args.model, faux=args.faux,
        runs=max(1, args.runs),
    )
    payload = {
        "tasks_file": str(tasks_path),
        "mode": "faux" if args.faux else "live",
        "provider": args.provider,
        "model": args.model or None,
        "runs": max(1, args.runs),
        **bench,
    }

    out_path: Optional[Path] = None
    if args.out:
        out_path = Path(args.out)
    elif args.save:
        fingerprint = config_fingerprint(payload)
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        out_path = RESULTS_DIR / f"{stamp}_{fingerprint}.json"
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(f"results written to {out_path}")
    print(render_summary(bench["results"], bench["summary"]))
    unstable = payload.get("unstable_ids") or []
    if unstable:
        print(f"unstable (dropped as flakes): {', '.join(unstable)}")
    return 0


def config_fingerprint(payload: Dict[str, Any]) -> str:
    """Stable short hash of the run's config for result-file naming."""
    import hashlib

    material = json.dumps(
        {
            k: payload.get(k)
            for k in ("tasks_file", "mode", "provider", "model", "runs")
        },
        sort_keys=True,
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:8]


if __name__ == "__main__":
    sys.exit(main())
