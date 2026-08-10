# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""S3-7 (J229): 429 backoff pins — Retry-After parsing.

Pins the 429 retry policy at the point of the decision
(agent.retry_utils.rate_limit_backoff_delay): a server-supplied
Retry-After wins when present and parseable (delta-seconds or HTTP-date,
capped at 120s); otherwise the jittered default backoff is used.
"""

import email.utils
import time

from agent.retry_utils import parse_retry_after, rate_limit_backoff_delay


def _default_bounds(base=2.0):
    """Jittered default backoff (base 2.0, jitter 0.5) lies in [base, 1.5*base)."""
    return base, base * 1.5


def test_429_without_headers_uses_default_backoff():
    lo, hi = _default_bounds()
    for headers in (None, {}):
        delay = rate_limit_backoff_delay(headers, attempt=1)
        assert lo <= delay < hi, (
            f"headers={headers}: expected default backoff in [{lo},{hi}), got {delay}"
        )


def test_429_with_retry_after_seconds_uses_header_delay():
    assert rate_limit_backoff_delay({"Retry-After": "5"}, attempt=3) == 5.0
    assert rate_limit_backoff_delay({"retry-after": "5"}, attempt=3) == 5.0
    assert parse_retry_after("5") == 5.0


def test_429_with_retry_after_http_date_uses_header_delay():
    future = time.time() + 7
    http_date = email.utils.formatdate(future, usegmt=True)
    delay = rate_limit_backoff_delay({"Retry-After": http_date}, attempt=3)
    assert 6.0 <= delay <= 7.0, f"expected ~7s from HTTP-date, got {delay}"


def test_malformed_retry_after_falls_back_to_default():
    lo, hi = _default_bounds()
    delay = rate_limit_backoff_delay({"Retry-After": "soon"}, attempt=1)
    assert lo <= delay < hi
    assert parse_retry_after("not-a-date") is None
    assert parse_retry_after("") is None


def test_negative_retry_after_falls_back_to_default():
    assert parse_retry_after("-5") is None
    lo, hi = _default_bounds()
    delay = rate_limit_backoff_delay({"Retry-After": "-5"}, attempt=1)
    assert lo <= delay < hi


def test_retry_after_delay_is_capped_at_max():
    assert parse_retry_after("99999") == 120.0
    assert parse_retry_after("99999", max_delay=60.0) == 60.0
    assert rate_limit_backoff_delay({"Retry-After": "10000"}, attempt=1) == 120.0
