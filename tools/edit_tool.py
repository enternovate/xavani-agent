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
  module-level default snapshot store (:data:`tools.hashline.snapshots.default_store`).
  Requires ``[path#TAG]`` sections whose tag matches the recorded snapshot
  for that path (the tag a future read tool will emit).  LIMITATION: the
  read tool does not yet emit tags (Task 12/15 follow-up), so callers must
  obtain the current tag from a prior ``hashline`` edit result or accept
  the auto-record behaviour below.  To keep the mode usable today, a path
  with no recorded snapshot is auto-recorded from its current on-disk
  content (full visible ranges) before applying, so ``[path#TAG]`` works
  when TAG is the fresh tag of the current content; a stale/unknown tag is
  rejected with an error string (nothing is written — fail-fast).  Because
  the read tool cannot supply the tag, that error re-reads the on-disk
  content itself and returns the fresh ``[path#TAG]`` to re-issue with —
  the first-edit loop is an explicit re-read flow, not an error-leak retry.
* ``replace`` — minimal exact old/new string substitution over one file
  (read, replace, write) using ``path`` / ``old_string`` / ``new_string``.

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
# Mode handlers
# ---------------------------------------------------------------------------


def _dispatch_patch(args: dict, task_id: str) -> str:
    """Delegate to the existing patch tool handler (V4A fuzzy strategies)."""
    from tools.file_tools import _handle_patch

    payload = args.get("input")
    if payload is None or not isinstance(payload, str) or not payload.strip():
        return tool_error("edit: mode='patch' requires a non-empty 'input' V4A patch payload")
    return _handle_patch({"mode": "patch", "patch": payload}, task_id=task_id)


def _full_ranges(content: str) -> Tuple[Tuple[int, int], ...]:
    """Visible-ranges tuple covering the whole file (used when auto-recording)."""
    lines = content.split("\n")
    if content.endswith("\n"):
        lines = lines[:-1]
    return ((1, len(lines)),) if lines else ()


def _hashline_tag_guidance(sections: List, msg: str) -> str:
    """Augment a stale/unknown-tag ApplyError with first-edit guidance.

    ``read_file`` does not emit ``[path#TAG]`` tags yet, so a bare
    "re-read the file" error is not actionable on a first edit.  The edit
    tool re-reads the on-disk content itself, records it (so the retry can
    resolve its tag), and returns the fresh ``[path#TAG]`` header(s) the
    model should re-issue with.  *msg* is returned unchanged when it is not
    a missing/stale-tag error.
    """
    if not any(k in msg for k in ("snapshot tag", "no snapshot recorded", "re-read")):
        return msg
    from tools.hashline.snapshots import default_store

    hints: List[str] = []
    for sec in sections:
        try:
            with open(sec.path, encoding="utf-8") as f:
                content = f.read()
        except OSError:
            continue
        fresh_tag = default_store.record(sec.path, content, ranges=_full_ranges(content))
        if fresh_tag != sec.tag:
            hints.append(f"[{sec.path}#{fresh_tag}]")
    if not hints:
        return msg
    return (
        f"{msg}\n"
        "NOTE: read_file does not emit [path#TAG] tags yet, so the edit "
        "tool re-read the file(s) on disk for you. Re-issue your edit with "
        f"{', '.join(hints)} to retry immediately (or read the file via "
        "read_file first, then edit with the tag above)."
    )


def _apply_hashline(args: dict, task_id: str) -> str:
    """Apply a hashline payload via the default snapshot store; never raises."""
    from contextlib import ExitStack

    from tools import file_state
    from tools.file_tools import (
        _check_file_staleness,
        _check_sensitive_path,
        _resolve_path_for_task,
        _update_read_timestamp,
    )
    from tools.hashline import ParseError, parse
    from tools.hashline.apply import ApplyError, apply_sections
    from tools.hashline.snapshots import default_store

    payload = args.get("input")
    if payload is None or not isinstance(payload, str) or not payload.strip():
        return tool_error("edit: mode='hashline' requires a non-empty 'input' payload")

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
    # between our auto-record reads, apply, and writes.  Unresolvable paths
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

        # Auto-record on-disk content for paths with no recorded snapshot, so
        # a [path#TAG] section whose tag matches the current content applies
        # even though read_file does not emit tags yet (Task 12/15 follow-up).
        for sec in sections:
            if default_store.get(sec.path) is not None:
                continue
            try:
                with open(sec.path, encoding="utf-8") as f:
                    content = f.read()
            except FileNotFoundError:
                # Leave unrecorded; apply_sections reports the missing snapshot.
                continue
            except OSError as exc:
                return tool_error(f"edit hashline: cannot read {sec.path}: {exc}")
            default_store.record(sec.path, content, ranges=_full_ranges(content))

        try:
            result = apply_sections(sections, default_store)
        except ApplyError as exc:
            # First-edit flow: read_file cannot supply the tag, so hand back
            # the fresh one the model can re-issue with (see docstring).
            return tool_error(_hashline_tag_guidance(sections, str(exc)))

        if result.error:
            return tool_error(f"edit hashline apply error: {result.error}")

        # Sensitive-path guard on FileResults too — an MV destination is a
        # write target the model never named in a section header.
        for fr in result.results:
            sensitive_err = _check_sensitive_path(fr.path, task_id)
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
                else:
                    parent = os.path.dirname(os.path.abspath(fr.path))
                    if parent:
                        os.makedirs(parent, exist_ok=True)
                    with open(fr.path, "w", encoding="utf-8") as f:
                        f.write(fr.preview)
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

    from tools import file_state
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
    replace_all = bool(args.get("replace_all", False))

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
        "with fuzzy matching), 'hashline' (line-anchored [path#TAG] sections; "
        "LIMITATION: read_file does not emit tags yet, so use the tag from a "
        "prior edit result or a fresh [path#TAG] against current content), and "
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
