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
  rejected with an error string (nothing is written — fail-fast).
* ``replace`` — minimal exact old/new string substitution over one file
  (read, replace, write) using ``path`` / ``old_string`` / ``new_string``.

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


def _apply_hashline(args: dict, task_id: str) -> str:
    """Apply a hashline payload via the default snapshot store; never raises."""
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

    # Auto-record on-disk content for paths with no recorded snapshot, so a
    # [path#TAG] section whose tag matches the current content applies even
    # though read_file does not emit tags yet (Task 12/15 follow-up).
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
        return tool_error(f"edit hashline apply error: {exc}")

    if result.error:
        return tool_error(f"edit hashline apply error: {result.error}")

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

    return json.dumps(
        {"ok": True, "mode": "hashline", "files": written, "warnings": result.warnings},
        ensure_ascii=False,
    )


def _apply_replace(args: dict, task_id: str) -> str:
    """Minimal exact old/new string replace over one file; never raises."""
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

    return json.dumps(
        {"ok": True, "mode": "replace", "path": path, "replaced": count},
        ensure_ascii=False,
    )


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
