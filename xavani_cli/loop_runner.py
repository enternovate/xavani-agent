# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Loop engine: persisted task loops with stop conditions and telemetry.

A loop is a JSON spec at ``~/.xavani/loops/<id>.json`` describing a prompt
plus stop conditions. Each pass calls an injected runner callable with the
prompt, the previous pass output, and the failure notes; the result feeds
telemetry and the next pass. State survives restarts, so a crashed loop
resumes from its last recorded pass.
"""

import json
import os
import time
import uuid
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

MAX_FAILURE_NOTES = 10
RUNAWAY_IDENTICAL_PASSES = 3

_loop_depth: ContextVar[int] = ContextVar("xavani_loop_depth", default=0)


def loops_dir() -> Path:
    override = os.environ.get("XAVANI_LOOPS_DIR")
    if override:
        return Path(override)
    return Path.home() / ".xavani" / "loops"


class LoopError(ValueError):
    pass


def new_loop(
    prompt: str,
    *,
    every_seconds: Optional[int] = None,
    until_predicate: Optional[str] = None,
    max_passes: int = 10,
    budget_usd: Optional[float] = None,
    wall_limit_seconds: Optional[int] = None,
    directory: Optional[Path] = None,
) -> Dict[str, Any]:
    """Create a loop spec on disk and return it."""
    if not prompt or not prompt.strip():
        raise LoopError("prompt must be a non-empty string")
    if max_passes < 1:
        raise LoopError("max_passes must be >= 1")
    if every_seconds is not None and every_seconds < 1:
        raise LoopError("every_seconds must be >= 1")
    if _loop_depth.get() >= 2:
        raise LoopError("nested loops beyond depth 2 are not allowed")
    spec = {
        "id": f"loop-{time.strftime('%Y%m%d_%H%M%S')}-{uuid.uuid4().hex[:6]}",
        "prompt": prompt,
        "every_seconds": every_seconds,
        "until_predicate": until_predicate,
        "max_passes": max_passes,
        "budget_usd": budget_usd,
        "wall_limit_seconds": wall_limit_seconds,
        "status": "active",
        "created_ts": time.time(),
        "passes": [],
        "failure_notes": [],
        "best_output": None,
    }
    _write(spec, directory)
    return spec


def load(loop_id: str, directory: Optional[Path] = None) -> Dict[str, Any]:
    path = (directory or loops_dir()) / f"{loop_id}.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise LoopError(f"loop not found: {loop_id}") from None
    except json.JSONDecodeError as exc:
        raise LoopError(f"loop spec corrupted ({loop_id}): {exc}") from None


def list_loops(directory: Optional[Path] = None) -> List[Dict[str, Any]]:
    base = directory or loops_dir()
    if not base.exists():
        return []
    specs = []
    for path in sorted(base.glob("loop-*.json")):
        try:
            specs.append(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    return specs


def stop(loop_id: str, directory: Optional[Path] = None) -> Dict[str, Any]:
    spec = load(loop_id, directory)
    spec["status"] = "stopped"
    _write(spec, directory)
    return spec


def record_failure_note(spec: Dict[str, Any], note: str,
                        directory: Optional[Path] = None) -> None:
    notes = spec.setdefault("failure_notes", [])
    notes.append(note)
    del notes[:-MAX_FAILURE_NOTES]
    _write(spec, directory)


def check_stop_conditions(
    spec: Dict[str, Any],
    *,
    elapsed_seconds: float = 0.0,
    spent_usd: float = 0.0,
) -> Optional[str]:
    """Return the stop reason when the loop must halt, else None."""
    passes_done = len(spec.get("passes", []))
    if spec.get("status") == "stopped":
        return "stopped by user"
    if passes_done >= int(spec.get("max_passes", 10)):
        return f"max passes reached ({passes_done})"
    budget = spec.get("budget_usd")
    if budget is not None and spent_usd >= float(budget):
        return f"budget cap reached (${spent_usd:.4f} >= ${float(budget):.4f})"
    wall = spec.get("wall_limit_seconds")
    if wall is not None and elapsed_seconds >= float(wall):
        return f"wall-clock limit reached ({elapsed_seconds:.0f}s >= {wall}s)"
    return None


def run_loop(
    spec: Dict[str, Any],
    runner: Callable[..., str],
    *,
    success_predicate: Optional[Callable[[str], bool]] = None,
    cost_per_pass_usd: float = 0.0,
    directory: Optional[Path] = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> Dict[str, Any]:
    """Run passes until a stop condition or the success predicate fires.

    ``runner(prompt=..., last_output=..., failure_notes=...)`` returns the
    pass output string. Each pass appends telemetry to the spec and writes
    it to disk immediately so a crash resumes at the next pass.
    """
    started = time.time()
    token = _loop_depth.set(_loop_depth.get() + 1)
    try:
        return _run_loop_inner(
            spec, runner,
            success_predicate=success_predicate,
            cost_per_pass_usd=cost_per_pass_usd,
            directory=directory, sleep_fn=sleep_fn, started=started,
        )
    finally:
        _loop_depth.reset(token)


def _run_loop_inner(
    spec: Dict[str, Any],
    runner: Callable[..., str],
    *,
    success_predicate: Optional[Callable[[str], bool]] = None,
    cost_per_pass_usd: float = 0.0,
    directory: Optional[Path] = None,
    sleep_fn: Callable[[float], None] = time.sleep,
    started: float,
) -> Dict[str, Any]:
    while True:
        stop_reason = check_stop_conditions(
            spec,
            elapsed_seconds=time.time() - started,
            spent_usd=sum(p.get("cost_usd", 0.0) for p in spec.get("passes", [])),
        )
        if stop_reason:
            spec["status"] = "completed"
            spec["stop_reason"] = stop_reason
            _write(spec, directory)
            return spec

        output = runner(
            prompt=spec["prompt"],
            last_output=spec.get("passes", [])[-1].get("output") if spec.get("passes") else None,
            failure_notes=list(spec.get("failure_notes", [])),
        )
        entry = {
            "n": len(spec.get("passes", [])) + 1,
            "ts": time.time(),
            "output": output,
            "duration_s": round(time.time() - started, 3),
            "cost_usd": cost_per_pass_usd,
        }
        spec.setdefault("passes", []).append(entry)

        if success_predicate is not None and success_predicate(output):
            spec["status"] = "completed"
            spec["stop_reason"] = f"success predicate met at pass {entry['n']}"
            spec["best_output"] = output
            _write(spec, directory)
            return spec

        if output:
            spec["best_output"] = output

        recent = [p["output"] for p in spec["passes"][-RUNAWAY_IDENTICAL_PASSES:]]
        if (
            len(recent) == RUNAWAY_IDENTICAL_PASSES
            and len(set(recent)) == 1
        ):
            spec["status"] = "completed"
            spec["stop_reason"] = (
                f"runaway detected: {RUNAWAY_IDENTICAL_PASSES} identical passes"
            )
            _write(spec, directory)
            return spec

        stop_reason = check_stop_conditions(
            spec, elapsed_seconds=time.time() - started,
            spent_usd=sum(p.get("cost_usd", 0.0) for p in spec.get("passes", [])),
        )
        if stop_reason:
            spec["status"] = "completed"
            spec["stop_reason"] = stop_reason
            _write(spec, directory)
            return spec

        gap = spec.get("every_seconds")
        if gap:
            sleep_fn(float(gap))


def _safe_score_at_least(score_fn: Callable[[str], float], output: str,
                         threshold: float) -> bool:
    try:
        return float(score_fn(output)) >= threshold
    except Exception:
        return False


def run_loop_eval(
    spec: Dict[str, Any],
    runner: Callable[..., str],
    score_fn: Callable[[str], float],
    threshold: float,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Eval loop: iterate until ``score_fn(output) >= threshold``.

    Each pass record gains a ``score`` field; scoring runs once per pass on
    the recorded output so scores stay reproducible.
    """
    result = run_loop(
        spec, runner,
        success_predicate=lambda out: _safe_score_at_least(score_fn, out, threshold),
        **kwargs,
    )
    directory = kwargs.get("directory")
    for entry in result.get("passes", []):
        try:
            entry["score"] = float(score_fn(entry["output"]))
        except Exception:
            entry["score"] = None
    _write(result, directory)
    return result


def load_rubric(path: str) -> List[str]:
    """Load verifier lines (contains:/regex:) from a rubric file."""
    lines = []
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            lines.append(line)
    if not lines:
        raise LoopError(f"rubric file has no verifier lines: {path}")
    return lines


def rubric_score(response: str, checks: List[str]) -> float:
    """Fraction of rubric verifier lines the response satisfies."""
    from scripts.task_bench.run_bench import parse_verifier

    if not checks:
        return 0.0
    passed = 0
    for line in checks:
        try:
            if parse_verifier(line)(response):
                passed += 1
        except Exception:
            continue
    return passed / len(checks)


def prune(max_age_days: int = 7, directory: Optional[Path] = None) -> List[str]:
    """Delete completed or stopped loop specs older than ``max_age_days``."""
    if max_age_days < 0:
        raise LoopError("max_age_days must be >= 0")
    cutoff = time.time() - max_age_days * 86400
    removed = []
    for spec in list_loops(directory):
        done = spec.get("status") in ("completed", "stopped")
        old = float(spec.get("created_ts", 0)) < cutoff
        if not (done and old):
            continue
        path = (directory or loops_dir()) / f"{spec['id']}.json"
        try:
            path.unlink()
            removed.append(spec["id"])
        except OSError:
            continue
    return removed


def save(spec: Dict[str, Any], directory: Optional[Path] = None) -> None:
    """Persist a loop spec update (public wrapper around _write)."""
    _write(spec, directory)


def summary(spec: Dict[str, Any]) -> str:
    passes = spec.get("passes", [])
    total_cost = sum(p.get("cost_usd", 0.0) for p in passes)
    lines = [
        f"{spec['id']}  status={spec['status']}  passes={len(passes)}",
        f"prompt: {spec['prompt'][:80]}",
        f"total cost: ${total_cost:.4f}",
    ]
    if spec.get("stop_reason"):
        lines.append(f"stopped: {spec['stop_reason']}")
    return "\n".join(lines)


def _write(spec: Dict[str, Any], directory: Optional[Path]) -> None:
    base = directory or loops_dir()
    base.mkdir(parents=True, exist_ok=True)
    tmp = base / f".{spec['id']}.tmp"
    tmp.write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(base / f"{spec['id']}.json")
