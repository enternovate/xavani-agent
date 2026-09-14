#!/usr/bin/env python3

# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Unified ``edit`` tool with mode selection (Task 15).

Three editing modes behind one wire name, with explicit per-call override
or configured resolution:

* ``patch`` (default) — delegates to the EXISTING patch tool handler
  (:func:`tools.file_tools._handle_patch`), i.e. the V4A patch format with
  the fuzzy matching strategies.  Behavior is unchanged from calling
  ``patch`` directly.
* ``hashline`` — parses the payload with :mod:`tools.hashline.parse` and
  applies it via :func:`tools.hashline.apply.apply_sections` against the
  snapshot store of the CALLING TASK
  (:func:`tools.hashline.snapshots.TaskSnapshotStores.for_task`), so a
  subagent can never edit lines another subagent read.  Requires
  ``[path#TAG]`` sections whose tag matches a snapshot the current task
  OBSERVED — the header ``read_file`` / ``search_files`` emitted for the
  lines they displayed.  The edit path never records or authorizes: a
  missing or stale tag writes nothing and returns the read-first contract
  (plus the header a fresh read will emit for the current content).
* ``replace`` — minimal exact old/new string substitution over one file
  (read, replace, write) using ``path`` / ``old_string`` / ``new_string``.

LIMITATION: unlike the ``patch`` / ``write_file`` tools, ``hashline`` and
``replace`` write files directly on the LOCAL filesystem via plain
``open()`` calls — they do not route through ``ShellFileOperations`` /
``file_ops`` like the rest of the file-tool family.  They are therefore
only correct when the terminal backend is local: with a non-local backend
(docker/modal/singularity/daytona/vercel_sandbox/ssh) active, the paths a
model names refer to the sandbox filesystem, and both modes refuse with a
clear error rather than silently editing the wrong file.

File-safety: ``hashline`` and ``replace`` route their writes through the
same guards as the ``patch`` / ``write_file`` tools — sensitive system
paths are rejected up front (:func:`tools.file_tools._check_sensitive_path`),
the read->modify->write region is serialized per-path with
:func:`tools.file_state.lock_path` (cross-agent staleness + per-task
warnings collected inside the lock), and successful writes refresh the
read timestamps via :func:`tools.file_tools._update_read_timestamp` and
:func:`tools.file_state.note_write`.  ``patch`` mode is unchanged.

Errors NEVER raise out of the tool: parse/apply/OS errors are returned as
JSON error result strings, matching the rest of the file-tool family.
"""

import json
import os
from typing import Dict, List, Optional, Tuple

from xavani_constants import get_config_path

from tools.registry import registry, tool_error

#: Per-model edit-mode table.  Resolution order: per-model variant ->
#: env ``XAVANI_EDIT_MODE`` -> config ``edit.mode`` -> :data:`DEFAULT_EDIT_MODE`.
#: Starts empty; populate e.g. ``{"claude-sonnet-4-5": "hashline"}`` to
#: opt specific models into a preferred mode ahead of env/config.
PER_MODEL_EDIT_MODE: Dict[str, str] = {}

DEFAULT_EDIT_MODE = "patch"
VALID_MODES = ("hashline", "patch", "replace")

#: ApplyError substrings that mean "this task has no usable observed snapshot".
_STALE_SNAPSHOT_MARKERS = (
    "no snapshot recorded",
    "no longer available",
    "recovery cannot prove",
    "the file changed since your read",
)

#: Contract message when a task edits lines it never observed.
_READ_FIRST_MESSAGE = (
    "Read the target lines before the edit. The current task has no "
    "observed snapshot for this file."
)


# ---------------------------------------------------------------------------
# Mode resolution
# ---------------------------------------------------------------------------


def resolve_edit_mode(model_name: Optional[str] = None) -> str:
    """Resolve the edit mode for a call.

    Order: per-model configured variant -> env ``XAVANI_EDIT_MODE`` ->
    config ``edit.mode`` -> default ``'patch'`` (existing behavior kept).
    """
    if model_name:
        per_model = PER_MODEL_EDIT_MODE.get(model_name)
        if per_model:
            return per_model
    env_mode = os.environ.get("XAVANI_EDIT_MODE")
    if env_mode:
        return env_mode
    cfg_mode = _config_edit_mode()
    if cfg_mode:
        return cfg_mode
    return DEFAULT_EDIT_MODE


def _config_edit_mode() -> Optional[str]:
    """Read ``edit.mode`` from ``config.yaml``; None when unset/unreadable."""
    try:
        import yaml

        cfg_path = get_config_path()
        if not cfg_path.exists():
            return None
        with open(cfg_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        edit = cfg.get("edit") or {}
        mode = edit.get("mode")
        return mode if isinstance(mode, str) and mode else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Local-backend guard (hashline/replace write directly on the host FS)
# ---------------------------------------------------------------------------


def _backend_is_local(task_id: str = "default") -> bool:
    """True when the terminal backend for *task_id* runs on the local host.

    ``hashline`` and ``replace`` modes write files with plain ``open()``
    calls on this process's filesystem, so they are only correct when the
    terminal backend is local — the same signal
    :func:`tools.file_tools._get_file_ops` uses (``TERMINAL_ENV`` config,
    plus the D07 untrusted-repo sandbox escalation).  With a container/cloud
    backend (docker/modal/singularity/daytona/vercel_sandbox/ssh) the paths
    a model names refer to the sandbox filesystem, not the host one this
    process writes; the caller must fail fast instead of editing the wrong
    file.  Fails closed (returns False) when the config cannot be read or
    does not name an explicit ``local`` backend, so an unknown backend is
    never mistaken for the host filesystem.
    """
    try:
        from tools.terminal_tool import _get_env_config

        config = _get_env_config()
    except Exception:
        return False
    return isinstance(config, dict) and config.get("env_type") == "local"


# ---------------------------------------------------------------------------
# Mode handlers
# ---------------------------------------------------------------------------


def _dispatch_patch(args: dict, task_id: str) -> str:
    """Delegate to the existing patch tool handler (V4A fuzzy strategies)."""
    from tools.file_tools import _handle_patch

    payload = args.get("input")
    if payload is None or not isinstance(payload, str) or not payload.strip():
        return tool_error("edit: mode='patch' requires a non-empty 'input' V4A patch payload")
    return _handle_patch({"mode": "patch", "patch": payload}, task_id=task_id)


def _hashline_tag_guidance(sections: List, msg: str, task_id: str) -> str:
    """Lead a missing/stale-snapshot ApplyError with the read-first contract.

    The tag is minted by the read tool, so the model must observe the target
    lines before editing.  When the file is readable its current header is
    included: the single re-read the model is told to perform returns exactly
    that header, making the retry one read away.  Nothing is recorded or
    authorized here.  *msg* is returned unchanged when it is not a
    missing/stale-snapshot error (e.g. a line outside the seen window).
    """
    if not any(k in msg for k in _STALE_SNAPSHOT_MARKERS):
        return msg
    from tools.file_tools import _resolve_path_for_task
    from tools.hashline.snapshots import compute_tag

    hints: List[str] = []
    for sec in sections:
        try:
            with open(sec.path, encoding="utf-8") as f:
                content = f.read()
        except OSError:
            continue
        try:
            shown = str(_resolve_path_for_task(sec.path, task_id))
        except Exception:
            shown = sec.path
        hints.append(f"[{shown}#{compute_tag(content)}]")
    out = [f"{_READ_FIRST_MESSAGE}\n{msg}"]
    if hints:
        out.append(
            "Read the file with read_file first — for the current content it "
            f"returns {', '.join(hints)}; re-issue the edit with that header."
        )
    return "\n".join(out)


def _apply_hashline(args: dict, task_id: str) -> str:
    """Apply a hashline payload via the calling task's snapshot store."""
    from contextlib import ExitStack

    from tools import file_state, fs_scan_cache
    from tools.file_tools import (
        _check_file_staleness,
        _check_sensitive_path,
        _resolve_path_for_task,
        _update_read_timestamp,
    )
    from tools.hashline import ParseError, parse
    from tools.hashline.apply import ApplyError, apply_sections
    from tools.hashline.snapshots import task_stores

    payload = args.get("input")
    if payload is None or not isinstance(payload, str) or not payload.strip():
        return tool_error("edit: mode='hashline' requires a non-empty 'input' payload")

    # Snapshots are per-task observations: an anonymous caller has no
    # provenance to authorize an edit with, and a shared store would let one
    # subagent edit lines only another subagent read.
    try:
        store = task_stores.for_task(task_id)
    except ValueError:
        return tool_error("edit hashline requires an explicit task identity.")

    # Local-only writes: hashline applies via plain open() on this host's
    # filesystem, so a non-local terminal backend must refuse up front.
    if not _backend_is_local(task_id):
        return tool_error(
            "edit: mode='hashline' writes files directly on the local "
            "filesystem, but the active TERMINAL_ENV backend is not local — "
            "the paths in this call would not edit the files the model "
            "sees. Use patch mode or re-run with the local backend."
        )

    try:
        sections = parse(payload)
    except ParseError as exc:
        return tool_error(f"edit hashline parse error: {exc}")

    # Sensitive-path guard on every section path, up front — same rejection
    # the patch/write_file tools apply (checked after realpath resolution).
    for sec in sections:
        sensitive_err = _check_sensitive_path(sec.path, task_id)
        if sensitive_err:
            return tool_error(sensitive_err)

    # Resolve + lock every section path in sorted order (mirrors
    # tools.file_tools.patch_tool) so concurrent subagents cannot interleave
    # between the tag resolution, apply, and writes.  Unresolvable paths
    # degrade to an unlocked no-op.
    resolved_paths: list = []
    _seen: set = set()
    for sec in sections:
        try:
            _r = str(_resolve_path_for_task(sec.path, task_id))
        except Exception:
            _r = None
        if _r and _r not in _seen:
            resolved_paths.append(_r)
            _seen.add(_r)
    resolved_paths.sort()

    with ExitStack() as _locks:
        for _r in resolved_paths:
            _locks.enter_context(file_state.lock_path(_r))

        # Staleness warnings — cross-agent registry first (names the sibling
        # subagent), per-task tracker as fallback; same precedence as patch.
        stale_warnings: list = []
        for sec in sections:
            try:
                _r = str(_resolve_path_for_task(sec.path, task_id))
            except Exception:
                _r = None
            _cross = file_state.check_stale(task_id, _r) if _r else None
            _sw = _cross or _check_file_staleness(sec.path, task_id)
            if _sw:
                stale_warnings.append(_sw)

        try:
            result = apply_sections(sections, store)
        except ApplyError as exc:
            # Nothing observed for this file/tag: hand back the read-first
            # contract (the tag is minted by the read tool, never here).
            return tool_error(_hashline_tag_guidance(sections, str(exc), task_id))

        if result.error:
            return tool_error(f"edit hashline apply error: {result.error}")

        # Sensitive-path guard on FileResults too — an MV destination is a
        # write target the model never named in a section header, and the
        # MV source must pass the same check (unlink target).
        for fr in result.results:
            sensitive_err = _check_sensitive_path(fr.path, task_id)
            if sensitive_err:
                return tool_error(sensitive_err)
            if fr.action == "move" and fr.source:
                sensitive_err = _check_sensitive_path(fr.source, task_id)
                if sensitive_err:
                    return tool_error(sensitive_err)

        written: List[dict] = []
        for fr in result.results:
            try:
                if fr.action == "remove":
                    try:
                        os.unlink(fr.path)
                    except FileNotFoundError:
                        pass
                    fs_scan_cache.invalidate(fr.path)
                else:
                    parent = os.path.dirname(os.path.abspath(fr.path))
                    if parent:
                        os.makedirs(parent, exist_ok=True)
                    with open(fr.path, "w", encoding="utf-8") as f:
                        f.write(fr.preview)
                    fs_scan_cache.invalidate(fr.path)
                    if fr.action == "move" and fr.source:
                        # MV: unlink the source ONLY after the destination
                        # write succeeded — a failed write must not lose the
                        # original file.
                        try:
                            os.unlink(fr.source)
                        except FileNotFoundError:
                            pass
                        except OSError as exc:
                            return tool_error(
                                f"edit hashline: destination {fr.path} written "
                                f"but failed to remove source {fr.source}: {exc}"
                            )
                        fs_scan_cache.invalidate(fr.source)
                written.append({"path": fr.path, "tag": fr.tag, "action": fr.action})
            except OSError as exc:
                return tool_error(f"edit hashline: failed to write {fr.path}: {exc}")

        # Refresh stamps after the successful writes so consecutive edits by
        # this task don't trigger false staleness warnings, and sibling
        # subagents see this task as the last writer (mirrors patch_tool).
        for fr in result.results:
            _update_read_timestamp(fr.path, task_id)
            try:
                _r = str(_resolve_path_for_task(fr.path, task_id))
            except Exception:
                _r = None
            if _r:
                file_state.note_write(task_id, _r)

    out: dict = {
        "ok": True,
        "mode": "hashline",
        "files": written,
        "warnings": result.warnings,
    }
    if stale_warnings:
        out["_warning"] = (
            stale_warnings[0] if len(stale_warnings) == 1
            else " | ".join(stale_warnings)
        )
    return json.dumps(out, ensure_ascii=False)


def _apply_replace(args: dict, task_id: str) -> str:
    """Minimal exact old/new string replace over one file; never raises."""
    from contextlib import nullcontext

    from tools import file_state, fs_scan_cache
    from tools.file_tools import (
        _check_file_staleness,
        _check_sensitive_path,
        _resolve_path_for_task,
        _update_read_timestamp,
    )

    path = args.get("path")
    old_string = args.get("old_string")
    if not path or not isinstance(path, str):
        return tool_error("edit: mode='replace' requires 'path'")
    if old_string is None or not isinstance(old_string, str):
        return tool_error("edit: mode='replace' requires 'old_string'")
    new_string = args.get("new_string", "")
    if new_string is None:
        new_string = ""
    if not isinstance(new_string, str):
        return tool_error(
            f"edit: mode='replace' 'new_string' must be a string, got "
            f"{type(new_string).__name__}"
        )
    replace_all = bool(args.get("replace_all", False))

    # Local-only writes: replace rewrites the file via plain open() on this
    # host's filesystem, so a non-local terminal backend must refuse up front.
    if not _backend_is_local(task_id):
        return tool_error(
            "edit: mode='replace' writes files directly on the local "
            "filesystem, but the active TERMINAL_ENV backend is not local — "
            "the path in this call would not edit the file the model sees. "
            "Use patch mode or re-run with the local backend."
        )

    # Sensitive-path guard — same rejection the patch/write_file tools apply.
    sensitive_err = _check_sensitive_path(path, task_id)
    if sensitive_err:
        return tool_error(sensitive_err)

    try:
        resolved = str(_resolve_path_for_task(path, task_id))
    except Exception:
        resolved = None

    # Serialize the read→modify→write region per-path so concurrent
    # subagents can't interleave on the same file (mirrors write_file_tool).
    with file_state.lock_path(resolved) if resolved else nullcontext():
        # Cross-agent staleness wins over per-task warning when both fire —
        # its message names the sibling subagent (mirrors write_file_tool).
        cross_warning = file_state.check_stale(task_id, resolved) if resolved else None
        stale_warning = _check_file_staleness(path, task_id)
        effective_warning = cross_warning or stale_warning

        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
        except OSError as exc:
            return tool_error(f"edit replace: {exc}")

        count = content.count(old_string)
        if count == 0:
            return tool_error(f"edit replace: old_string not found in {path}")
        if not replace_all and count > 1:
            return tool_error(
                f"edit replace: old_string occurs {count} times in {path}; "
                "pass replace_all=True or include more context"
            )

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content.replace(old_string, new_string))
        except OSError as exc:
            return tool_error(f"edit replace: {exc}")
        fs_scan_cache.invalidate(path)

        # Refresh stamps after the successful write so consecutive edits by
        # this task don't trigger false staleness warnings (mirrors patch).
        _update_read_timestamp(path, task_id)
        if resolved:
            file_state.note_write(task_id, resolved)

    out: dict = {"ok": True, "mode": "replace", "path": path, "replaced": count}
    if effective_warning:
        out["_warning"] = effective_warning
    return json.dumps(out, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Handler + registration
# ---------------------------------------------------------------------------


def _handle_edit(args: dict, **kw) -> str:
    """Registry handler: resolve mode, route to the mode implementation."""
    task_id = kw.get("task_id") or "default"
    mode = args.get("mode") or resolve_edit_mode()
    if mode not in VALID_MODES:
        return tool_error(
            f"edit: unknown mode {mode!r}; valid modes: hashline, patch, replace"
        )
    if mode == "patch":
        return _dispatch_patch(args, task_id)
    if mode == "hashline":
        return _apply_hashline(args, task_id)
    return _apply_replace(args, task_id)


EDIT_SCHEMA = {
    "name": "edit",
    "description": (
        "Unified file-edit tool with mode selection. "
        "Modes: 'patch' (default, same as the patch tool: V4A multi-file patches "
        "with fuzzy matching), 'hashline' (line-anchored [path#TAG] sections "
        "whose tag must come from a read_file/search_files header THIS task "
        "observed; edits may only target lines the current task was shown), and "
        "'replace' (exact old/new string substitution via path/old_string/new_string). "
        "The mode can be overridden per call; otherwise it resolves from the model "
        "variant, XAVANI_EDIT_MODE, config edit.mode, or defaults to 'patch'."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "input": {
                "type": "string",
                "description": (
                    "Patch payload: V4A patch text for mode='patch'; hashline "
                    "[path#TAG] sections for mode='hashline'. Unused by mode='replace'."
                ),
            },
            "mode": {
                "type": "string",
                "enum": ["hashline", "patch", "replace"],
                "description": (
                    "Optional per-call mode override. When omitted, resolves from "
                    "the model variant -> env XAVANI_EDIT_MODE -> config edit.mode "
                    "-> default 'patch'."
                ),
            },
            "path": {
                "type": "string",
                "description": "REQUIRED when mode='replace'. File path to edit.",
            },
            "old_string": {
                "type": "string",
                "description": (
                    "REQUIRED when mode='replace'. Exact text to find. Must be "
                    "unique unless replace_all=true."
                ),
            },
            "new_string": {
                "type": "string",
                "description": (
                    "REQUIRED when mode='replace'. Replacement text. Pass empty "
                    "string '' to delete the matched text."
                ),
            },
            "replace_all": {
                "type": "boolean",
                "description": "Replace all occurrences (mode='replace' only; default false)",
                "default": False,
            },
        },
    },
}


def _check_file_reqs():
    """Lazy wrapper to avoid circular import with tools/__init__.py."""
    from tools import check_file_requirements

    return check_file_requirements()


registry.register(
    name="edit",
    toolset="file",
    schema=EDIT_SCHEMA,
    handler=_handle_edit,
    check_fn=_check_file_reqs,
    emoji="✏️",
    max_result_size_chars=100_000,
)
