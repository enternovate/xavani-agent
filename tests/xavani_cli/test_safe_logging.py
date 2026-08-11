# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for :mod:`xavani_cli.safe_logging`.

The module is the chokepoint for secret redaction across every log
emitter, so the test surface deliberately leans on real ``logging``
machinery (root logger, handlers, formatters) rather than mocks. We want
to catch regressions where a refactor breaks redaction in the actual
emission path, not just in the helper functions.
"""

from __future__ import annotations

import io
import logging
import re

import pytest

from xavani_cli import safe_logging
from xavani_cli.safe_logging import (
    REDACTION,
    SafeFormatter,
    SafeLogFilter,
    add_pattern,
    install,
    is_installed,
    redact,
    remove_pattern,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_global_state():
    """Strip any state added by previous tests on the root logger."""
    root = logging.getLogger()
    pre_filters = list(root.filters)
    try:
        yield
    finally:
        for f in list(root.filters):
            if f not in pre_filters:
                root.removeFilter(f)
        # Re-initialise the install singleton so each test starts clean.
        safe_logging._installed_filter = None  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# redact() — pure function
# ---------------------------------------------------------------------------


class TestRedactProviderPrefixes:
    """Every recognised provider-prefix token should be redacted in full."""

    @pytest.mark.parametrize(
        "secret",
        [
            "sk-abcdefghijklmnopqrstuvwxyz1234",
            "sk-proj-abcdefghijklmnopqrstuvwxyz1234",
            "sk-org-abcdefghijklmnopqrstuvwxyz1234",
            "sk-ant-abcdefghijklmnopqrstuvwxyz1234",
            "xai-abcdefghijklmnopqrstuvwxyz1234",
            "gsk_abcdefghijklmnopqrstuvwxyz1234",
            "sess-abcdefghijklmnopqrstuvwxyz",
            "sk_live_abcdefghijklmnopqrstuvwxyz1234",
            "pk_test_abcdefghijklmnopqrstuvwxyz1234",
            "ghp_abcdefghijklmnopqrstuvwxyz1234abcdef",
            "gho_abcdefghijklmnopqrstuvwxyz1234abcdef",
            "xoxb-abcdefghijklmnopqrstuv",
            "xoxp-abcdefghijklmnopqrstuv",
            "AKIAIOSFODNN7EXAMPLE",
            "ASIAIOSFODNN7EXAMPLE",
            "AROAIOSFODNN7EXAMPLE",
            "AIzaSyA0123456789ABCDEFGHIJKLMNOPQRSTUVW",
        ],
    )
    def test_known_prefixes_redacted(self, secret: str) -> None:
        msg = f"key={secret} more"
        assert REDACTION in redact(msg)
        assert secret not in redact(msg)

    def test_jwt_token_redacted(self) -> None:
        jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        assert REDACTION in redact(jwt)
        assert jwt not in redact(jwt)

    def test_slack_webhook_redacted(self) -> None:
        url = "https://hooks.slack.com/services/T01ABCDEF/B01ABCDEF/abcdef1234567890ABCDEFGH"
        assert url not in redact(url)


class TestRedactTransport:
    """Authorization headers and URL-embedded creds are scrubbed."""

    def test_bearer_token(self) -> None:
        assert REDACTION in redact("Authorization: Bearer abcdef1234567890abcdef1234567890")

    def test_basic_auth(self) -> None:
        assert REDACTION in redact("Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=")

    def test_url_embedded_credentials(self) -> None:
        original = "Fetching https://admin:hunter2@example.com/api"
        scrubbed = redact(original)
        assert "hunter2" not in scrubbed
        assert "admin" not in scrubbed

    def test_oauth_user_code(self) -> None:
        assert REDACTION in redact("Visit https://login.example.com/device?user_code=ABCD-EFGH")

    def test_oauth_token_params(self) -> None:
        assert REDACTION in redact("/callback?access_token=abcd1234efgh5678ijkl9012")
        assert REDACTION in redact("/callback?refresh_token=abcd1234efgh5678ijkl9012")


class TestRedactPrivateKeys:
    def test_pem_marker_redacted(self) -> None:
        pem = "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA..."
        assert "-----BEGIN" not in redact(pem) or REDACTION in redact(pem)


class TestRedactBroadFallback:
    def test_long_hex_redacted(self) -> None:
        long_hex = "ab" * 24  # 48 chars
        msg = f"hash={long_hex} more"
        assert REDACTION in redact(msg)

    def test_short_hex_not_redacted(self) -> None:
        # 40-char git SHA shouldn't trip the fallback
        short_hex = "0123456789abcdef0123456789abcdef01234567"
        assert short_hex in redact(f"commit {short_hex}")

    def test_uuid_not_redacted(self) -> None:
        uuid = "550e8400-e29b-41d4-a716-446655440000"
        assert uuid in redact(f"id={uuid}")


class TestRedactEdgeCases:
    def test_empty_string(self) -> None:
        assert redact("") == ""

    def test_no_secrets_unchanged(self) -> None:
        plain = "hello world, nothing to see here"
        assert redact(plain) == plain

    def test_explicit_pattern_set(self) -> None:
        custom = (re.compile(r"\bSECRET-[A-Z0-9]+\b"),)
        assert REDACTION in redact("token=SECRET-ABC123", patterns=custom)
        # Default patterns aren't applied when explicit set is passed
        assert "sk-abcdefghijklmnopqrstuvwxyz1234" in redact(
            "key=sk-abcdefghijklmnopqrstuvwxyz1234", patterns=custom
        )


# ---------------------------------------------------------------------------
# SafeLogFilter
# ---------------------------------------------------------------------------


class TestSafeLogFilter:
    def test_message_redacted_in_emitted_output(self) -> None:
        buf = io.StringIO()
        handler = logging.StreamHandler(buf)
        handler.setFormatter(logging.Formatter("%(message)s"))
        log = logging.getLogger("safe_logging.test1")
        log.handlers.clear()
        log.addFilter(SafeLogFilter())
        log.addHandler(handler)
        log.setLevel(logging.INFO)

        log.info("API key=%s here", "sk-abcdefghijklmnopqrstuvwxyz1234")
        output = buf.getvalue()
        assert "sk-abcdefghijklmnopqrstuvwxyz1234" not in output
        assert REDACTION in output

    def test_exc_info_redacted(self) -> None:
        buf = io.StringIO()
        handler = logging.StreamHandler(buf)
        handler.setFormatter(logging.Formatter("%(message)s"))
        log = logging.getLogger("safe_logging.test2")
        log.handlers.clear()
        log.addFilter(SafeLogFilter())
        log.addHandler(handler)
        log.setLevel(logging.INFO)

        secret = "sk-abcdefghijklmnopqrstuvwxyz1234"
        try:
            raise RuntimeError(f"failed with token={secret}")
        except RuntimeError:
            log.exception("upstream blew up")

        output = buf.getvalue()
        assert secret not in output

    def test_args_cleared_after_redaction(self) -> None:
        """Cleared args prevent the formatter from resurrecting raw secrets."""
        record = logging.LogRecord(
            name="t", level=logging.INFO, pathname="x", lineno=1,
            msg="key=%s", args=("sk-abcdefghijklmnopqrstuvwxyz1234",), exc_info=None,
        )
        SafeLogFilter().filter(record)
        assert record.args == ()
        assert record.msg == "key=[REDACTED]"


# ---------------------------------------------------------------------------
# SafeFormatter
# ---------------------------------------------------------------------------


class TestSafeFormatter:
    def test_formatter_wraps_inner(self) -> None:
        inner = logging.Formatter("%(levelname)s :: %(message)s")
        f = SafeFormatter(inner)
        rec = logging.LogRecord(
            name="t", level=logging.WARNING, pathname="x", lineno=1,
            msg="leak=sk-abcdefghijklmnopqrstuvwxyz1234", args=(), exc_info=None,
        )
        out = f.format(rec)
        assert out.startswith("WARNING :: ")
        assert "sk-abcdefghijklmnopqrstuvwxyz1234" not in out
        assert REDACTION in out


# ---------------------------------------------------------------------------
# install()
# ---------------------------------------------------------------------------


class TestInstall:
    def test_install_is_idempotent(self) -> None:
        f1 = install()
        f2 = install()
        assert f1 is f2

    def test_install_attaches_to_root(self) -> None:
        f = install()
        root = logging.getLogger()
        assert f in root.filters

    def test_install_attaches_to_explicit_logger(self) -> None:
        target = logging.getLogger("xavani.safe_logging.test_install_target")
        f = install(target)
        assert f in target.filters

    def test_is_installed_tracks_state(self) -> None:
        assert is_installed() is False
        install()
        assert is_installed() is True


# ---------------------------------------------------------------------------
# add_pattern / remove_pattern
# ---------------------------------------------------------------------------


class TestCustomPatterns:
    def test_add_and_match(self) -> None:
        pat = add_pattern(r"\bCUSTOM-[A-Z]{4}\b")
        try:
            assert REDACTION in redact("token=CUSTOM-ABCD")
        finally:
            remove_pattern(pat)

    def test_remove_returns_false_when_unregistered(self) -> None:
        pat = re.compile(r"\bnever-registered\b")
        assert remove_pattern(pat) is False

    def test_pattern_compiled_lazily(self) -> None:
        pat = add_pattern(r"\bTEST-PATTERN-[0-9]+\b", flags=re.IGNORECASE)
        try:
            assert REDACTION in redact("see test-pattern-9999")
        finally:
            remove_pattern(pat)
