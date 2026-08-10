#!/usr/bin/env python3

# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Edit-format benchmark harness (Task 16).

Runs canned edit tasks through the REAL edit tool paths and reports a JSON
summary plus a human table:

* ``--mode patch``    -> :func:`tools.edit_tool._handle_edit` mode='patch',
                         which delegates to :func:`tools.file_tools._handle_patch`
                         (V4A patch format with fuzzy matching strategies).
* ``--mode hashline`` -> ``_handle_edit`` mode='hashline' (tools.hashline
                         parse + apply via the default snapshot store).
* ``--mode replace``  -> ``_handle_edit`` mode='replace' (exact old/new
                         string substitution).

Two model paths:

* ``--model fake`` (default) — uses the canned payload stored on each task
  record in ``tasks.jsonl``.  Deterministic, no provider key, CI-safe.
  Proves the harness and every real tool path work end to end.
* ``--model live`` — calls a real model to generate the tool payload from
  the task prompt (env ``XAVANI_EDIT_MODEL`` + ``XAVANI_API_KEY``, optional
  ``XAVANI_API_BASE`` defaulting to an OpenAI-compatible
  ``/chat/completions`` endpoint), applies it through the same tool path,
  and judges the result.  Requires a live provider key; documented in
  docs/reference/edit-benchmark.md.

Contract:

* STDOUT is pure JSON: a summary object ``{mode, model, tasks_total, passed,
  failed, total_retries, total_tokens_est, tasks: [...]}`` — safe to pipe
  into ``python3 -m json.tool``.
* The human table goes to STDERR.
* Exit 0 when every task was attempted; exit 1 on fatal errors (unknown
  mode, missing tasks file, live mode without env keys) with an error JSON
  object on stdout.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

# Make ``tools.*`` importable when run as a script from anywhere.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.edit_tool import VALID_MODES, _handle_edit  # noqa: E402
from tools.hashline.snapshots import compute_tag, default_store  # noqa: E402

DEFAULT_TASKS = Path(__file__).resolve().parent / "tasks.jsonl"

#: Hashline payloads are authored with a ``#TAG`` placeholder; the runner
#: refreshes it to ``compute_tag(original_content)`` before applying so the
#: canned payload never goes stale if an original is edited later.
_HASHLINE_TAG_RE = re.compile(r"(\[[^#\]]+)#TAG\]")


class BenchmarkError(Exception):
    """Fatal harness error -> error JSON on stdout + exit 1."""


# ---------------------------------------------------------------------------
# Task loading
# ---------------------------------------------------------------------------


def load_tasks(path: Path, max_tasks: int | None = None) -> list[dict]:
    if not path.exists():
        raise BenchmarkError(f"tasks file not found: {path}")
    tasks = []
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                tasks.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise BenchmarkError(f"{path}:{lineno}: invalid JSON: {exc}")
    if max_tasks is not None:
        tasks = tasks[:max_tasks]
    if not tasks:
        raise BenchmarkError(f"no tasks loaded from {path}")
    return tasks


# ---------------------------------------------------------------------------
# Temp tree + payload shaping
# ---------------------------------------------------------------------------


def write_originals(task: dict, root: Path) -> dict[str, str]:
    """Write each task file's original content; return {abs_path: content}."""
    content_by_path: dict[str, str] = {}
    for entry in task.get("files", []):
        target = root / entry["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(entry["original"], encoding="utf-8")
        content_by_path[str(target)] = entry["original"]
    return content_by_path


def absolutize_payload(task: dict, mode: str, payload, root: Path):
    """Rewrite relative file paths in a canned payload to absolute paths."""
    rel_to_abs = {f["path"]: str(root / f["path"]) for f in task.get("files", [])}
    if mode == "replace":
        items = list(payload)
        for item in items:
            item["path"] = rel_to_abs[item["path"]]
        return items
    if mode == "hashline":
        text = payload
        for rel, abs_path in rel_to_abs.items():
            text = text.replace(f"[{rel}#", f"[{abs_path}#")
        return text
    if mode == "patch":
        text = payload
        for rel, abs_path in rel_to_abs.items():
            text = text.replace(f"*** Update File: {rel}", f"*** Update File: {abs_path}")
        return text
    return payload


def refresh_hashline_tags(payload: str, content_by_path: dict[str, str]) -> str:
    """Replace ``#TAG`` placeholders with ``compute_tag(original)``."""

    def _sub(match: re.Match) -> str:
        path = match.group(1)[1:]
        return f"[{path}#{compute_tag(content_by_path[path])}]"

    return _HASHLINE_TAG_RE.sub(_sub, payload)


def payload_text(payload) -> str:
    """Canonical payload text for token estimation (approx chars/4)."""
    return payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)


def payload_tokens(payload) -> int:
    return max(1, len(payload_text(payload)) // 4)


# ---------------------------------------------------------------------------
# Applying through the real tool path
# ---------------------------------------------------------------------------


def apply_payload(mode: str, payload, root: Path) -> dict:
    """Invoke the real edit tool path; return parsed JSON result dict."""
    if mode == "replace":
        result: dict = {"ok": True, "mode": "replace", "applied": 0}
        for item in payload:
            out = json.loads(_handle_edit({"mode": "replace", **item}, task_id="edit_benchmark"))
            if not out.get("ok"):
                return out
            result["applied"] += 1
        return result
    if mode == "hashline":
        # Invalidate every path we are about to touch so auto-record in
        # _apply_hashline re-records the on-disk (original) content.
        for path in _task_abs_paths_from_payload(payload):
            default_store.invalidate(path)
        return json.loads(_handle_edit({"mode": "hashline", "input": payload}, task_id="edit_benchmark"))
    # patch mode: the tool reports {"success": true/false}; normalize to the
    # {"ok": bool} contract the caller uses.
    result = json.loads(_handle_edit({"mode": "patch", "input": payload}, task_id="edit_benchmark"))
    if "ok" not in result and "success" in result:
        result["ok"] = bool(result["success"])
    return result


def _task_abs_paths_from_payload(payload: str) -> list[str]:
    return re.findall(r"^\[([^#\]]+)#[0-9A-F]{4}\]", payload, re.MULTILINE)


def files_match_targets(task: dict, root: Path) -> str | None:
    """Compare every file against its target; return a diff-ish note or None."""
    for entry in task.get("files", []):
        path = root / entry["path"]
        if not path.exists():
            return f"{entry['path']}: missing after edit"
        actual = path.read_text(encoding="utf-8")
        if actual != entry["target"]:
            a_lines, t_lines = actual.splitlines(), entry["target"].splitlines()
            for i, (a, t) in enumerate(zip(a_lines, t_lines), 1):
                if a != t:
                    return f"{entry['path']}: line {i} differs:\n  got:      {a!r}\n  expected: {t!r}"
            return f"{entry['path']}: {len(a_lines)} vs {len(t_lines)} lines"
    return None


# ---------------------------------------------------------------------------
# Model paths: fake (canned) vs live (provider key)
# ---------------------------------------------------------------------------


def build_payload_fake(task: dict, mode: str) -> object:
    payloads = task.get("payloads") or {}
    if mode not in payloads:
        raise BenchmarkError(
            f"task {task['id']}: no canned {mode} payload (fake mode)"
        )
    return payloads[mode]


def build_payload_live(task: dict, mode: str, root: Path, feedback: str | None = None) -> object:
    """Ask a real model for the tool payload (best-effort; needs a key).

    Uses env ``XAVANI_EDIT_MODEL`` + ``XAVANI_API_KEY`` and an optional
    ``XAVANI_API_BASE`` (default OpenAI-compatible ``/chat/completions``).
    """
    model = os.environ.get("XAVANI_EDIT_MODEL")
    api_key = os.environ.get("XAVANI_API_KEY")
    if not model or not api_key:
        raise BenchmarkError(
            "live mode requires XAVANI_EDIT_MODEL and XAVANI_API_KEY env vars "
            "(use --model fake for the CI-safe deterministic path)"
        )
    base = os.environ.get("XAVANI_API_BASE", "https://api.openai.com/v1").rstrip("/")

    files_block = "\n\n".join(
        f"--- {entry['path']} ---\n{entry['original']}"
        for entry in task.get("files", [])
    )
    mode_guide = {
        "patch": "V4A patch text: '*** Begin Patch' / '*** Update File: <path>' / "
                 "'@@ hint @@' / context lines, -removed, +added / '*** End Patch'.",
        "hashline": "hashline text: '[<path>#TAG]' section headers (TAG=4 hex, any value "
                    "is accepted) followed by ops such as 'PUT 2.=2:' with '+<line>' body rows.",
        "replace": "a JSON array of {\"path\", \"old_string\", \"new_string\"} objects, one per file.",
    }[mode]
    prompt = (
        f"Edit task: {task['description']}\n"
        f"Language: {task['language']}\n"
        f"Operation hint: {task['operation']}\n\n"
        f"Current file contents:\n{files_block}\n\n"
        f"Produce the edit-tool payload that applies this change, in this format:\n{mode_guide}\n"
        + (f"\nThe previous attempt failed. Fix it: {feedback}\n" if feedback else "")
        + "\nRespond with ONLY the payload JSON (a string for hashline/patch, an array for replace)."
    )
    body = {
        "model": model,
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": "You emit edit-tool payloads for a file-editing agent. "
                "Return only the payload: no prose, no markdown code fences.",
            },
            {"role": "user", "content": prompt},
        ],
    }
    req = urllib.request.Request(
        base + "/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise BenchmarkError(f"live model HTTP {exc.code}: {exc.read().decode(errors='replace')[:300]}")
    except OSError as exc:
        raise BenchmarkError(f"live model call failed: {exc}")
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise BenchmarkError(f"live model unexpected response: {exc}")
    return extract_json(text)


def extract_json(text: str) -> object:
    """Pull the first JSON value out of a model reply (tolerates fences)."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    for match in re.finditer(r"(\{.*\}|\[.*\])", cleaned, re.DOTALL):
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
    raise BenchmarkError("live model reply contained no parseable JSON payload")


# ---------------------------------------------------------------------------
# Task execution
# ---------------------------------------------------------------------------


def run_task(task: dict, mode: str, model: str, root: Path, max_retries: int) -> dict:
    content_by_path = write_originals(task, root)
    record = {
        "id": task["id"],
        "description": task.get("description", ""),
        "status": "fail",
        "retries": 0,
        "tokens_est": 0,
        "error": None,
    }
    feedback: str | None = None
    for attempt in range(max_retries + 1):
        if attempt:
            record["retries"] += 1
            write_originals(task, root)  # restore pristine originals
        try:
            if model == "fake":
                payload = build_payload_fake(task, mode)
            else:
                payload = build_payload_live(task, mode, root, feedback)
        except BenchmarkError as exc:
            record["error"] = str(exc)
            break
        record["tokens_est"] += payload_tokens(payload)

        try:
            # Absolutize payload paths FIRST (relative -> temp tree), then
            # refresh hashline #TAG placeholders against the on-disk originals.
            payload = absolutize_payload(task, mode, payload, root)
            if mode == "hashline":
                payload = refresh_hashline_tags(str(payload), content_by_path)
            result = apply_payload(mode, payload, root)
        except Exception as exc:  # tool paths never raise, but be defensive
            result = {"error": f"{type(exc).__name__}: {exc}"}

        if result.get("ok"):
            mismatch = files_match_targets(task, root)
            if mismatch is None:
                record["status"] = "pass"
                break
            feedback = mismatch
        else:
            feedback = str(result.get("error", "tool error"))
    else:
        record["error"] = record.get("error") or feedback
    return record


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def print_table(summary: dict) -> None:
    rows = summary["tasks"]
    print(f"\nmode={summary['mode']} model={summary['model']} "
          f"tasks={summary['tasks_total']} passed={summary['passed']} "
          f"failed={summary['failed']} retries={summary['total_retries']} "
          f"tokens_est={summary['total_tokens_est']}", file=sys.stderr)
    print(f"{'id':<6} {'status':<6} {'retries':<8} {'tokens':<8} description", file=sys.stderr)
    print("-" * 78, file=sys.stderr)
    for t in rows:
        err = f"  ({t['error']})" if t.get("error") else ""
        print(f"{t['id']:<6} {t['status']:<6} {t['retries']:<8} {t['tokens_est']:<8} "
              f"{t.get('description', '')[:52]}{err}", file=sys.stderr)
    print(file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Edit-format benchmark harness (Task 16).")
    parser.add_argument("--mode", choices=list(VALID_MODES), default="hashline",
                        help="edit mode under test (default: hashline)")
    parser.add_argument("--model", choices=["fake", "live"], default="fake",
                        help="payload source: fake canned payloads (CI-safe) or live model call")
    parser.add_argument("--tasks", type=Path, default=DEFAULT_TASKS,
                        help="path to tasks.jsonl (default: alongside this script)")
    parser.add_argument("--max-tasks", type=int, default=None,
                        help="only run the first N tasks")
    parser.add_argument("--max-retries", type=int, default=3,
                        help="max re-attempts per task (default 3)")
    args = parser.parse_args(argv)

    try:
        tasks = load_tasks(args.tasks, args.max_tasks)
        summary: dict = {
            "mode": args.mode,
            "model": args.model,
            "tasks_total": len(tasks),
            "passed": 0,
            "failed": 0,
            "total_retries": 0,
            "total_tokens_est": 0,
            "tasks": [],
        }
        with tempfile.TemporaryDirectory(prefix="edit_benchmark_") as tmp:
            root = Path(tmp)
            for task in tasks:
                record = run_task(task, args.mode, args.model, root / task["id"], args.max_retries)
                summary["tasks"].append(record)
                summary["total_retries"] += record["retries"]
                summary["total_tokens_est"] += record["tokens_est"]
                if record["status"] == "pass":
                    summary["passed"] += 1
                else:
                    summary["failed"] += 1
        print_table(summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    except BenchmarkError as exc:
        print(json.dumps({"error": str(exc), "mode": args.mode, "model": args.model},
                         ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
