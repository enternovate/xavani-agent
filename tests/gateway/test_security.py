# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for :mod:`gateway.security`.

The module is the chokepoint for path-traversal and SSRF defence across
the gateway. Tests exercise the real filesystem (via ``tmp_path``) and
the real address parser — DNS resolution is exercised via IP literals
so the suite stays hermetic and runs offline.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from gateway import security
from gateway.security import (
    PathValidationError,
    URLValidationError,
    assert_safe_url,
    is_safe_url,
    validate_path,
)


# ---------------------------------------------------------------------------
# validate_path
# ---------------------------------------------------------------------------


class TestValidatePath:
    def test_relative_path_within_base(self, tmp_path: Path) -> None:
        target = tmp_path / "subdir" / "file.txt"
        target.parent.mkdir()
        target.write_text("hi")
        out = validate_path("subdir/file.txt", tmp_path)
        assert out == target.resolve()

    def test_relative_traversal_blocked(self, tmp_path: Path) -> None:
        # Even though the file might exist outside the base, the
        # traversal-as-input should be refused.
        outside = tmp_path.parent / "escaped.txt"
        outside.write_text("x")
        try:
            with pytest.raises(PathValidationError, match="escapes"):
                validate_path("../escaped.txt", tmp_path)
        finally:
            outside.unlink(missing_ok=True)

    def test_absolute_outside_base_blocked(self, tmp_path: Path) -> None:
        with pytest.raises(PathValidationError):
            validate_path("/etc/passwd", tmp_path)

    def test_string_prefix_trick_blocked(self, tmp_path: Path) -> None:
        """``/tmp/base-evil`` must not pass when base is ``/tmp/base``."""
        base = tmp_path / "base"
        base.mkdir()
        evil = tmp_path / "base-evil"
        evil.mkdir()
        (evil / "f.txt").write_text("x")
        with pytest.raises(PathValidationError):
            validate_path("../base-evil/f.txt", base)

    def test_missing_file_without_allow_create(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            validate_path("nope.txt", tmp_path)

    def test_missing_file_with_allow_create(self, tmp_path: Path) -> None:
        # Parent (tmp_path) exists, target may be missing.
        out = validate_path("new.txt", tmp_path, allow_create=True)
        assert out.parent == tmp_path.resolve()

    def test_allow_create_rejects_escaped_parent(self, tmp_path: Path) -> None:
        with pytest.raises(PathValidationError):
            validate_path("../escape/new.txt", tmp_path, allow_create=True)

    def test_symlink_to_outside_followed_and_blocked(self, tmp_path: Path) -> None:
        if os.name == "nt":
            pytest.skip("Symlink creation requires privilege on Windows")
        outside = tmp_path.parent / "outside"
        outside.mkdir(exist_ok=True)
        (outside / "leak.txt").write_text("secret")
        link = tmp_path / "evil"
        try:
            link.symlink_to(outside)
        except OSError:
            pytest.skip("Symlink creation not supported in this environment")
        with pytest.raises(PathValidationError):
            validate_path("evil/leak.txt", tmp_path)
        # Cleanup outside the tmp tree.
        (outside / "leak.txt").unlink()
        outside.rmdir()

    def test_symlink_no_follow(self, tmp_path: Path) -> None:
        """``follow_symlinks=False`` lets writers ignore the symlink target."""
        if os.name == "nt":
            pytest.skip("Symlink creation requires privilege on Windows")
        inside = tmp_path / "real"
        inside.mkdir()
        link = tmp_path / "alias"
        try:
            link.symlink_to(inside)
        except OSError:
            pytest.skip("Symlink creation not supported")
        # When we do not follow symlinks, the link's pure path remains
        # inside the base, so the call must succeed.
        out = validate_path("alias", tmp_path, follow_symlinks=False)
        assert out == (tmp_path / "alias")

    def test_forbidden_null_byte(self, tmp_path: Path) -> None:
        with pytest.raises(PathValidationError, match="forbidden control byte"):
            validate_path("a\x00.txt", tmp_path, allow_create=True)

    def test_forbidden_newline(self, tmp_path: Path) -> None:
        with pytest.raises(PathValidationError, match="forbidden control byte"):
            validate_path("file\n.txt", tmp_path, allow_create=True)


# ---------------------------------------------------------------------------
# assert_safe_url
# ---------------------------------------------------------------------------


class TestSchemeFiltering:
    @pytest.mark.parametrize("url", ["ftp://example.com", "file:///etc/passwd", "javascript:alert(1)", "data:text/html,..."])
    def test_disallowed_schemes_rejected(self, url: str) -> None:
        with pytest.raises(URLValidationError, match="scheme"):
            assert_safe_url(url)

    def test_custom_scheme_set(self) -> None:
        assert is_safe_url("ws://1.1.1.1/", allow_schemes=frozenset({"ws"}))

    def test_empty_url(self) -> None:
        with pytest.raises(URLValidationError):
            assert_safe_url("")


class TestHostnameFiltering:
    def test_missing_hostname_rejected(self) -> None:
        # urlparse returns no hostname for "https:///path"
        with pytest.raises(URLValidationError, match="hostname"):
            assert_safe_url("https:///path")

    def test_localhost_rejected_by_name(self) -> None:
        with pytest.raises(URLValidationError):
            assert_safe_url("http://localhost/")

    def test_dot_local_suffix_rejected(self) -> None:
        with pytest.raises(URLValidationError):
            assert_safe_url("http://router.local/")


class TestPrivateRangeBlocking:
    @pytest.mark.parametrize(
        "url",
        [
            "http://127.0.0.1/",
            "http://10.0.0.5/",
            "http://192.168.1.10/",
            "http://172.16.0.5/",
            "http://[::1]/",
        ],
    )
    def test_private_or_loopback_rejected(self, url: str) -> None:
        with pytest.raises(URLValidationError):
            assert_safe_url(url)

    @pytest.mark.parametrize(
        "url",
        [
            "http://127.0.0.1/",
            "http://192.168.1.10/",
        ],
    )
    def test_allow_localhost_permits(self, url: str) -> None:
        # allow_localhost makes private + loopback OK
        assert is_safe_url(url, allow_localhost=True)


class TestCloudMetadataBlocking:
    @pytest.mark.parametrize(
        "url",
        [
            "http://169.254.169.254/latest/meta-data",   # AWS / Azure / GCP / DO / Oracle / Hetzner
            "http://169.254.169.254/computeMetadata/v1", # GCP form
            "http://100.100.100.200/latest/meta-data",   # Alibaba Cloud
            "http://100.64.0.5/",                        # RFC 6598 CGN range
        ],
    )
    def test_metadata_endpoints_rejected(self, url: str) -> None:
        with pytest.raises(URLValidationError, match="metadata|link-local"):
            assert_safe_url(url)

    def test_metadata_blocked_even_with_allow_localhost(self) -> None:
        """Cloud metadata is blocked regardless of localhost override."""
        with pytest.raises(URLValidationError, match="metadata"):
            assert_safe_url("http://169.254.169.254/", allow_localhost=True)

    def test_alibaba_metadata_blocked_even_with_allow_localhost(self) -> None:
        with pytest.raises(URLValidationError, match="metadata"):
            assert_safe_url("http://100.100.100.200/", allow_localhost=True)


class TestMulticastUnspecified:
    def test_unspecified_rejected(self) -> None:
        with pytest.raises(URLValidationError, match="unspecified"):
            assert_safe_url("http://0.0.0.0/")

    def test_multicast_rejected(self) -> None:
        with pytest.raises(URLValidationError, match="multicast"):
            assert_safe_url("http://224.0.0.1/")


class TestPublicAllowed:
    @pytest.mark.parametrize(
        "url",
        [
            "https://example.com/",
            "https://api.anthropic.com/v1/messages",
            "https://1.1.1.1/",  # Cloudflare public DNS
            "http://8.8.8.8/",   # Google public DNS
        ],
    )
    def test_public_addresses_allowed(self, url: str) -> None:
        assert is_safe_url(url)


class TestIsSafeUrlWrapper:
    def test_returns_bool(self) -> None:
        assert is_safe_url("https://example.com/") is True
        assert is_safe_url("http://localhost/") is False

    def test_swallowed_exceptions(self) -> None:
        """``is_safe_url`` must never raise — it just returns False."""
        assert is_safe_url("not a url at all") is False
        # urlparse is lenient and may not raise, but we want the predicate
        # interface either way.
        assert is_safe_url("") is False


# ---------------------------------------------------------------------------
# Network metadata sets remain exported
# ---------------------------------------------------------------------------


class TestExports:
    def test_cloud_metadata_sets_exposed(self) -> None:
        assert security.CLOUD_METADATA_IPV4
        assert security.CLOUD_METADATA_IPV6

    def test_exceptions_exported(self) -> None:
        assert issubclass(PathValidationError, ValueError)
        assert issubclass(URLValidationError, ValueError)
