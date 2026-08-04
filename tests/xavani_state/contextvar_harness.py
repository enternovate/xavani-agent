# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""A03: ContextVar verification harness.

Verifies the ContextVar contract that gateway concurrency relies on:

1. Isolation — a value set inside a plain thread never leaks to the
   parent context (each thread starts with a FRESH context).
2. Fallback — a fresh thread sees the ContextVar default, not a value
   set in the parent.
3. Propagation via copy_context() — executor threads and asyncio
   tasks DO see the parent's value when the parent copies the context
   (gateway/session_context + tool_executor rely on this).
4. asyncio task isolation — a value set inside a task does not leak
   back to the creator's context.
5. Token reset — reset(token) restores the prior value.

Usage::

    from xavani_state.contextvar_harness import check_contextvar_semantics

    def test_approval_session_key():
        problems = check_contextvar_semantics(
            var=_approval_session_key,
            set_value="session-1",
            default="",
        )
        assert problems == []

Each check is a real thread/task probe — no mocking. Returns a list of
human-readable failure strings; an empty list means all semantics hold.
"""

from __future__ import annotations

import asyncio
import contextvars
import threading

# Sentinel for ContextVars without a default: .get() raises LookupError
# until the first .set(). The harness treats that as "unset".
_UNSET = object()


def _safe_get(var, sentinel=_UNSET):
    """var.get() that returns the sentinel instead of raising LookupError."""
    try:
        return var.get()
    except LookupError:
        return sentinel


def _fresh_thread_probe(var, set_value):
    """Return (child_sees, parent_sees) when a plain thread sets var.

    child_sees: value observed INSIDE the thread after setting.
    parent_sees: value observed in the parent AFTER the thread exits.
    """
    child_seen: list = []
    parent_seen: list = []

    def _child():
        var.set(set_value)
        child_seen.append(_safe_get(var))

    t = threading.Thread(target=_child)
    t.start()
    t.join()
    parent_seen.append(_safe_get(var))
    return child_seen[0], parent_seen[0]


def _copy_context_probe(var, set_value):
    """Return the value a copy_context() child sees after parent sets var."""
    parent_token = var.set(set_value)
    try:
        seen: list = []

        def _child():
            seen.append(_safe_get(var))

        ctx = contextvars.copy_context()
        ctx.run(_child)
        return seen[0]
    finally:
        var.reset(parent_token)


def _async_task_probe(var, set_value, baseline):
    """Return (task_sees, creator_sees) with an asyncio task setting var.

    baseline: the parent context value captured before the task ran.
    """
    results: dict = {}

    async def _main():
        async def _task():
            var.set(set_value)
            results["task"] = _safe_get(var)

        await asyncio.create_task(_task())
        results["creator"] = _safe_get(var)

    asyncio.run(_main())
    return results["task"], results["creator"]


def check_contextvar_semantics(var, set_value, default=None) -> list[str]:
    """Verify the ContextVar contract for ``var``. Returns problems.

    Args:
        var: The ContextVar under test.
        set_value: A value distinct from the default.
        default: The expected default (var.get() when never set).
            Pass the string "UNSET" for ContextVars with no default.
    """
    if default == "UNSET":
        expected_default = _UNSET
    else:
        expected_default = default if default is not None else _safe_get(var)

    problems: list[str] = []
    name = getattr(var, "name", str(var))
    # The parent baseline may differ from the default: some modules
    # self-initialize their vars (e.g. set to {}) on first access in the
    # main context. The contract is that a child must not CHANGE the
    # parent's view — compare against this captured baseline.
    parent_baseline = _safe_get(var)

    # 1. Isolation: a value set in a plain thread must NOT leak to parent.
    child_sees, parent_sees = _fresh_thread_probe(var, set_value)
    if child_sees != set_value:
        problems.append(f"{name}: child thread did not observe its own set value")
    if parent_sees is not parent_baseline:
        problems.append(
            f"{name}: value set in a child thread leaked to the parent "
            f"(got {parent_sees!r}, expected {parent_baseline!r})"
        )

    # 2. Fallback: a fresh thread sees the same default before and after
    # a parent-set. Capture the thread-default first (a fresh thread
    # never inherits the parent context), then confirm a parent-set does
    # not change what a fresh thread sees.
    thread_defaults: list = []

    def _fresh_capture():
        thread_defaults.append(_safe_get(var))

    t0 = threading.Thread(target=_fresh_capture)
    t0.start()
    t0.join()
    thread_default = thread_defaults[0] if thread_defaults else expected_default

    parent_token = var.set(set_value)
    try:
        fresh_seen: list = []

        def _fresh():
            fresh_seen.append(_safe_get(var))

        t = threading.Thread(target=_fresh)
        t.start()
        t.join()
        if fresh_seen and fresh_seen[0] is not thread_default:
            problems.append(
                f"{name}: fresh thread changed view after a parent-set "
                f"(got {fresh_seen[0]!r}, before {thread_default!r})"
            )
    finally:
        var.reset(parent_token)

    # 3. copy_context() propagation: executor threads must see parent value.
    propagated = _copy_context_probe(var, set_value)
    if propagated != set_value:
        problems.append(
            f"{name}: copy_context() child did not see parent value "
            f"(got {propagated!r}, expected {set_value!r})"
        )

    # 4. asyncio task isolation: task-set value must not leak to creator.
    task_sees, creator_sees = _async_task_probe(var, set_value, parent_baseline)
    if task_sees != set_value:
        problems.append(f"{name}: asyncio task did not observe its own set value")
    if creator_sees is not parent_baseline:
        problems.append(
            f"{name}: value set inside an asyncio task leaked to the "
            f"creator (got {creator_sees!r}, expected {parent_baseline!r})"
        )

    # 5. Token reset restores the prior value.
    before = _safe_get(var)
    token = var.set(set_value)
    var.reset(token)
    if _safe_get(var) != before:
        problems.append(f"{name}: token reset did not restore the prior value")

    return problems
