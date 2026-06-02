# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for sandbox hardening (v0.4.0 U42)."""

from __future__ import annotations

import sys

import pytest

from tools import sandbox_hardening as sh


def test_is_linux_matches_platform():
    assert sh.is_linux() == sys.platform.startswith("linux")


def test_kernel_status_reports_seccomp_and_landlock():
    status = sh.kernel_sandbox_status()
    assert {"seccomp", "landlock"} <= set(status)
    if not sh.is_linux():
        for mech in ("seccomp", "landlock"):
            assert status[mech]["available"] is False
            assert "linux" in str(status[mech]["reason"]).lower()


def test_apply_resource_limits_maps_portable_limits():
    resource = pytest.importorskip("resource")
    calls = []
    fake_set = lambda const, vals: calls.append((const, vals))      # noqa: E731
    fake_get = lambda const: (0, resource.RLIM_INFINITY)            # noqa: E731

    result = sh.apply_resource_limits(
        cpu_seconds=5, open_files=64, setter=fake_set, getter=fake_get
    )
    assert result.applied is True
    consts = {c for c, _ in calls}
    # RLIMIT_CPU and RLIMIT_NOFILE exist on both macOS and Linux.
    assert resource.RLIMIT_CPU in consts
    assert resource.RLIMIT_NOFILE in consts
    # Values passed through as (soft, hard) tuples.
    by_const = dict(calls)
    assert by_const[resource.RLIMIT_NOFILE][0] == 64


def test_apply_resource_limits_never_exceeds_hard_cap():
    resource = pytest.importorskip("resource")
    calls = []
    fake_set = lambda const, vals: calls.append((const, vals))      # noqa: E731
    fake_get = lambda const: (0, 32)                                # hard cap = 32  # noqa: E731

    sh.apply_resource_limits(open_files=9999, setter=fake_set, getter=fake_get)
    soft, hard = dict(calls)[resource.RLIMIT_NOFILE]
    assert soft == 32 and hard == 32        # clamped to the hard cap


def test_apply_resource_limits_with_no_request_is_noop():
    resource = pytest.importorskip("resource")
    result = sh.apply_resource_limits(setter=lambda *a: None, getter=lambda c: (0, resource.RLIM_INFINITY))
    assert result.applied is False
