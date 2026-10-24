# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""First-party portal detection must cover the Enternovate inference host."""

from __future__ import annotations

import pytest

from utils import is_portal_base_url


@pytest.mark.parametrize(
    "base_url",
    [
        "https://inference-api.enternovate.co.za/v1",
        "https://inference-api.enternovate.co.za",
        "https://api.nousresearch.com/v1",
    ],
)
def test_first_party_portals_are_detected(base_url: str) -> None:
    assert is_portal_base_url(base_url) is True


@pytest.mark.parametrize(
    "base_url",
    [
        "https://openrouter.ai/api/v1",
        "https://evil.example/inference-api.enternovate.co.za/v1",
        "https://inference-api.enternovate.co.za.evil.example/v1",
        "",
    ],
)
def test_other_hosts_are_rejected(base_url: str) -> None:
    assert is_portal_base_url(base_url) is False
