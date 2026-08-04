# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests in this directory are QUARANTINED (A17).

They carry ``@pytest.mark.flaky`` and live in ``tests/flaky/`` so the build
can tell them apart from the stable suite at a glance.  They still run (run
them explicitly, or let the full suite collect them) but they must never
block CI: keep every test here deterministic-passing, and treat any failure
as a signal to either stabilise the test or delete it.
"""
