# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Fixtures shared across xavani_cli kanban tests."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _mock_validate_critical_files_syntax(monkeypatch, request):
    """Stub out ``_validate_critical_files_syntax`` for tests that call ``cmd_update``.

    ``xavani_cli.main._validate_critical_files_syntax`` calls
    ``py_compile.compile`` on the project's source files.  Under a parallel
    xdist run (10 workers), multiple workers write and rename the same
    ``__pycache__/*.pyc.<PID>`` temp files simultaneously, causing
    intermittent ``[Errno 2] No such file or directory`` errors that leave
    the ``.update_exit_code`` marker unwritten and tests failing.

    We stub out the function at the ``xavani_cli.main`` module level (not
    at ``py_compile`` level) so that tests in
    ``test_update_post_pull_syntax_guard.py`` — which specifically test
    ``_validate_critical_files_syntax`` through the module's own reference —
    are NOT affected.  Those tests import directly from ``xavani_cli.main``
    and access the function by name, bypassing this fixture entirely.
    """
    # Skip for tests that explicitly test _validate_critical_files_syntax
    # (they live in test_update_post_pull_syntax_guard.py).
    if "post_pull_syntax" in request.fspath.basename:
        return

    import xavani_cli.main as _main
    monkeypatch.setattr(_main, "_validate_critical_files_syntax", lambda *_a, **_k: (True, None, None))


@pytest.fixture
def all_assignees_spawnable(monkeypatch):
    """Pretend every assignee maps to a real Xavani profile.

    Most dispatcher tests use synthetic assignees ("alice", "bob") that
    don't correspond to actual profile directories on disk. Without this
    patch, the dispatcher's profile-exists guard (PR #20105) routes
    those tasks into ``skipped_nonspawnable`` instead of spawning, which
    would break tests that assert spawn behavior.
    """
    from xavani_cli import profiles
    monkeypatch.setattr(profiles, "profile_exists", lambda name: True)
