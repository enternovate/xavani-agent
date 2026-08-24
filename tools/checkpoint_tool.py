# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""
Checkpoint tool — model-invocable wrapper around ``CheckpointManager``.

Exposes the transparent filesystem-snapshot infrastructure (see
``tools/checkpoint_manager.py``, also behind the ``/rewind`` slash command)
as a ``checkpoint`` tool so the model can take, inspect, diff, and roll
back snapshots on demand:

- ``create``  — take a fresh snapshot of ``working_dir``
- ``list``    — list available checkpoints (most recent first)
- ``diff``    — show changes between a checkpoint and the current tree
- ``restore`` — revert files to a checkpoint (optionally a single file)

The tool owns its own manager instance (independent of the agent's
transparent auto-checkpointing); callers may substitute one via
``set_checkpoint_manager()`` (used by tests and embedders). Handlers never
raise — every outcome is returned as a JSON string with a ``success`` flag.
"""

import json
import os
import threading
from typing import Any, Dict, Optional

from tools.checkpoint_manager import CheckpointManager
from tools.registry import registry

_ACTIONS = ("create", "list", "diff", "restore")

_DEFAULT_MAX_RESULT_SIZE_CHARS = 20_000

_manager_lock = threading.Lock()
_manager: Optional[CheckpointManager] = None


def get_checkpoint_manager() -> CheckpointManager:
    """Return the shared manager, creating an enabled one on first use."""
    global _manager
    with _manager_lock:
        if _manager is None:
            _manager = CheckpointManager(enabled=True)
        return _manager


def set_checkpoint_manager(manager: Optional[CheckpointManager]) -> None:
    """Replace the shared manager (None restores lazy default creation)."""
    global _manager
    with _manager_lock:
        _manager = manager


def _resolve_working_dir(args: Dict[str, Any]) -> str:
    """Resolve ``working_dir`` from args, defaulting to the current directory."""
    raw = args.get("working_dir")
    if raw is None or not str(raw).strip():
        return os.getcwd()
    return os.path.abspath(os.path.expanduser(str(raw)))


def _error_payload(action: Optional[str], message: str) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"success": False, "error": message}
    if action is not None:
        payload["action"] = action
    return payload


def checkpoint_tool(args: Optional[Dict[str, Any]]) -> str:
    """Execute a checkpoint action and return the result as a JSON string.

    Never raises: unexpected failures are reported as
    ``{"success": false, "error": ...}``.
    """
    if not isinstance(args, dict):
        args = {}
    action = args.get("action")

    try:
        if not isinstance(action, str) or action not in _ACTIONS:
            return json.dumps(
                _error_payload(
                    None,
                    f"action must be one of {', '.join(_ACTIONS)}",
                )
            )

        manager = get_checkpoint_manager()
        working_dir = _resolve_working_dir(args)

        if action == "create":
            reason = str(args.get("reason") or "model checkpoint request")
            manager.new_turn()
            taken = bool(manager.ensure_checkpoint(working_dir, reason))
            payload: Dict[str, Any] = {
                "success": True,
                "action": action,
                "checkpoint_taken": taken,
                "enabled": bool(getattr(manager, "enabled", False)),
                "working_dir": working_dir,
                "reason": reason,
            }
            if taken:
                snapshots = manager.list_checkpoints(working_dir)
                if snapshots:
                    payload["checkpoint"] = snapshots[0]
            return json.dumps(payload, default=str)

        if action == "list":
            checkpoints = manager.list_checkpoints(working_dir)
            return json.dumps(
                {
                    "success": True,
                    "action": action,
                    "working_dir": working_dir,
                    "count": len(checkpoints),
                    "checkpoints": checkpoints,
                },
                default=str,
            )

        commit_hash = args.get("commit_hash")
        if not isinstance(commit_hash, str) or not commit_hash.strip():
            return json.dumps(
                _error_payload(action, f"{action} requires commit_hash")
            )

        if action == "diff":
            result = manager.diff(working_dir, commit_hash)
        else:
            file_path = args.get("file_path")
            if isinstance(file_path, str) and file_path.strip():
                result = manager.restore(working_dir, commit_hash, str(file_path))
            else:
                result = manager.restore(working_dir, commit_hash)

        payload = {
            "success": bool(result.get("success")),
            "action": action,
            "working_dir": working_dir,
            ("diff" if action == "diff" else "restored"): result,
        }
        if not payload["success"] and result.get("error"):
            payload["error"] = result["error"]
        return json.dumps(payload, default=str)

    except Exception as exc:
        return json.dumps(_error_payload(action, f"{type(exc).__name__}: {exc}"))


_CHECKPOINT_SCHEMA = {
    "type": "function",
    "description": (
        "Filesystem checkpointing: take, list, diff, and restore point-in-time "
        "snapshots of a working directory (shadow-git backed, independent of any "
        "repo the project itself uses). Actions: 'create' takes a fresh snapshot; "
        "'list' shows available checkpoints (most recent first, with hashes); "
        "'diff' compares a checkpoint against the current tree; 'restore' reverts "
        "files back to a checkpoint (a pre-rollback safety snapshot is taken "
        "automatically)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "list", "diff", "restore"],
                "description": "What to do.",
            },
            "working_dir": {
                "type": "string",
                "description": (
                    "Directory to snapshot/restore. Omit to use the current "
                    "working directory."
                ),
            },
            "commit_hash": {
                "type": "string",
                "description": (
                    "Checkpoint hash (from 'list') — required for 'diff' and "
                    "'restore'."
                ),
            },
            "file_path": {
                "type": "string",
                "description": (
                    "restore only: relative path to restore a single file "
                    "instead of the whole directory."
                ),
            },
            "reason": {
                "type": "string",
                "description": "create only: short label recorded with the snapshot.",
            },
        },
        "required": ["action"],
    },
}


def _check_checkpoint_requirements() -> bool:
    """Always available — the shadow store needs nothing beyond git (lazy-probed)."""
    return True


def _handle_checkpoint(args: Optional[Dict[str, Any]], **kw: Any) -> str:
    return checkpoint_tool(args)


registry.register(
    name="checkpoint",
    toolset="file",
    schema=_CHECKPOINT_SCHEMA,
    handler=_handle_checkpoint,
    check_fn=_check_checkpoint_requirements,
    emoji="⏮️",
    max_result_size_chars=_DEFAULT_MAX_RESULT_SIZE_CHARS,
)
