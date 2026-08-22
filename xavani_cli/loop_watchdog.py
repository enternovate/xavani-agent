# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Watchdog loops: cron-scheduled passes for the loop engine.

A watchdog loop runs on the cron scheduler instead of blocking a chat
session. Each scheduled tick executes at most one pass through
``xavani -z`` (oneshot mode) and records telemetry into the loop spec.

Watchdog contract: a tick prints nothing while the loop runs; when the
loop finishes it prints the summary alert and removes its cron job.
"""

import json
import os
import subprocess
import sys
import time
from typing import Any, Callable, Dict, Optional

from xavani_cli import loop_runner

DEFAULT_PASS_TIMEOUT_S = 600


def pass_timeout_s() -> int:
    raw = os.getenv("XAVANI_WATCHDOG_PASS_TIMEOUT", "").strip()
    if raw:
        try:
            value = int(float(raw))
            if value > 0:
                return value
        except ValueError:
            pass
    return DEFAULT_PASS_TIMEOUT_S


def build_pass_prompt(spec: Dict[str, Any]) -> str:
    """Compose one pass prompt from the spec (notes + previous output)."""
    prompt = spec["prompt"]
    notes = list(spec.get("failure_notes", []))
    if notes:
        rendered = "\n".join(f"- {n}" for n in notes)
        prompt += (
            f"\n\nFailure notes from earlier passes (avoid repeating "
            f"these mistakes):\n{rendered}"
        )
    passes = spec.get("passes", [])
    if passes:
        last = passes[-1].get("output")
        if last:
            prompt += (
                f"\n\nPrevious pass output:\n<previous_output>\n"
                f"{last[:4000]}\n</previous_output>"
            )
    return prompt


def headless_pass(prompt: str, timeout_s: Optional[int] = None) -> str:
    """Run one pass through ``xavani -z`` and return its stdout."""
    timeout = timeout_s or pass_timeout_s()
    try:
        result = subprocess.run(
            [sys.executable, "-m", "xavani", "-z", prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return f"(pass error: timed out after {timeout}s)"
    except OSError as exc:
        return f"(pass error: {exc})"
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        return f"(pass error: exit {result.returncode}: {detail[:500]})"
    output = (result.stdout or "").strip()
    return output or "(empty response)"


def _remove_linked_job(job_id: Optional[str]) -> None:
    if not job_id:
        return
    try:
        from cron.jobs import remove_job

        remove_job(job_id)
    except Exception:
        # A stale job id must never block the final alert.
        pass


def _finalize(
    spec: Dict[str, Any],
    reason: str,
    directory: Optional[Any],
) -> Dict[str, Any]:
    spec["status"] = "completed"
    spec["stop_reason"] = reason
    loop_runner.save(spec, directory)
    _remove_linked_job(spec.get("cron_job_id"))
    return {"action": "completed", "reason": reason, "spec": spec}


def tick(
    loop_id: str,
    *,
    pass_fn: Callable[[str], str] = headless_pass,
    directory: Optional[Any] = None,
) -> Dict[str, Any]:
    """Advance a watchdog loop by at most one pass.

    Returns an action dict: ``finished`` (spec already done),
    ``completed`` (a stop condition fired), or ``ran`` (one pass done).
    """
    spec = loop_runner.load(loop_id, directory)
    if spec.get("status") in ("completed", "stopped"):
        _remove_linked_job(spec.get("cron_job_id"))
        return {"action": "finished", "spec": spec}

    elapsed = time.time() - float(spec.get("created_ts", time.time()))
    spent = sum(p.get("cost_usd", 0.0) for p in spec.get("passes", []))
    stop = loop_runner.check_stop_conditions(spec, elapsed_seconds=elapsed, spent_usd=spent)
    if stop:
        return _finalize(spec, stop, directory)

    started = time.time()
    try:
        output = pass_fn(build_pass_prompt(spec))
    except Exception as exc:
        output = f"(pass error: {exc})"
    entry = {
        "n": len(spec.get("passes", [])) + 1,
        "ts": time.time(),
        "output": output,
        "duration_s": round(time.time() - started, 3),
        "cost_usd": 0.0,
    }
    spec.setdefault("passes", []).append(entry)

    recent = [
        p["output"]
        for p in spec["passes"][-loop_runner.RUNAWAY_IDENTICAL_PASSES:]
    ]
    if len(recent) == loop_runner.RUNAWAY_IDENTICAL_PASSES and len(set(recent)) == 1:
        return _finalize(
            spec,
            f"runaway detected: {loop_runner.RUNAWAY_IDENTICAL_PASSES} identical passes",
            directory,
        )

    elapsed = time.time() - float(spec.get("created_ts", time.time()))
    spent = sum(p.get("cost_usd", 0.0) for p in spec.get("passes", []))
    stop = loop_runner.check_stop_conditions(spec, elapsed_seconds=elapsed, spent_usd=spent)
    if stop:
        return _finalize(spec, stop, directory)

    loop_runner.save(spec, directory)
    return {"action": "ran", "spec": spec}


def wrapper_script_source(loop_id: str) -> str:
    """Source of the ~/.xavani/scripts/ job script for one watchdog loop."""
    return (
        "import sys\n\n"
        "from xavani_cli import loop_watchdog\n\n"
        f"sys.exit(loop_watchdog.main([{loop_id!r}]))\n"
    )


def main(argv: Optional[list] = None) -> int:
    """CLI entry: silent while running, summary alert when finished."""
    args = list(sys.argv[1:] if argv is None else argv)
    directory = None
    if "--dir" in args:
        i = args.index("--dir")
        if i + 1 < len(args):
            from pathlib import Path

            directory = Path(args[i + 1])
            del args[i : i + 2]
    if not args:
        sys.stderr.write("usage: python -m xavani_cli.loop_watchdog <loop-id> [--dir PATH]\n")
        return 2
    loop_id = args[0]
    try:
        result = tick(loop_id, directory=directory)
    except loop_runner.LoopError as exc:
        sys.stderr.write(f"watchdog tick failed: {exc}\n")
        return 1
    if result["action"] == "ran":
        return 0
    print(json.dumps(result, default=str, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
