# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Quarantine example (A17).

This is the template for the flaky-test quarantine zone at ``tests/flaky/``.
Tests here are inherently timing-sensitive (network, real processes) and
carry ``@pytest.mark.flaky``.  They run but never block CI — every test in
this directory must be deterministic-passing; a failure here means the test
needs stabilising or deleting, not patching around.

To quarantine an existing test: move it here, add ``@pytest.mark.flaky``,
and make it robust (deadline-based waits, no fixed sleeps).
"""

import pytest


@pytest.mark.flaky
def test_quarantine_example_is_deterministic():
    """A deterministic pass — quarantine is for *potentially* flaky tests,
    not for tests that are allowed to fail."""
    assert 1 + 1 == 2


@pytest.mark.flaky
def test_quarantine_example_carries_the_marker():
    """The flaky marker must be registered (pyproject.toml markers list),
    otherwise pytest warns about an unknown marker."""
    assert pytest.mark.flaky is not None
