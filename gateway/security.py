# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Security helpers for path validation and URL safety.

This module is the chokepoint for two recurring attack-surface classes
across the gateway and CLI:

* **Path traversal** — anywhere a user-supplied path is joined onto a
  trusted base directory (workspace, skills cache, MCP install dir, etc.)
  call :func:`validate_path` rather than ``Path(base) / user_path``. The
  helper canonicalises, refuses paths containing NUL or carriage-return
  bytes, follows symlinks, and verifies the resolved target sits inside
  the resolved base using :meth:`pathlib.PurePath.is_relative_to` so that
  string-prefix tricks (``"/tmp/base-evil"`` vs ``"/tmp/base"``) cannot
  slip past.

* **Server-Side Request Forgery (SSRF)** — anywhere a URL is fetched on
  behalf of the agent (web tools, MCP install, OpenAPI bridge, OAuth
  callbacks), validate it through :func:`is_safe_url` or call
  :func:`assert_safe_url` for a hard failure. The validator rejects
  non-HTTP(S) schemes, hostnames that resolve into RFC 1918/4193 private
  ranges, loopback/link-local space (which covers the cloud metadata
  endpoints at ``169.254.169.254`` on AWS/Azure/GCP/Oracle/Hetzner),
  carrier-grade NAT (Aliyun's metadata at ``100.100.100.200``), and the
  IPv6 equivalents.

The cloud-metadata block list is enforced even when ``allow_localhost`` is
True, because development overrides should never be a foot-gun for
exfiltration of instance-role credentials.
"""

from __future__ import annotations

import ipaddress
import os
import socket
from pathlib import Path
from typing import Final, FrozenSet, Optional, Tuple, Union
from urllib.parse import urlparse

__all__ = [
    "PathValidationError",
    "URLValidationError",
    "validate_path",
    "is_safe_url",
    "assert_safe_url",
    "CLOUD_METADATA_IPV4",
    "CLOUD_METADATA_IPV6",
]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class PathValidationError(ValueError):
    """Raised when :func:`validate_path` rejects a candidate path."""


class URLValidationError(ValueError):
    """Raised when :func:`assert_safe_url` rejects a candidate URL."""


# ---------------------------------------------------------------------------
# Cloud-metadata blocklist
# ---------------------------------------------------------------------------
# The IPv4 link-local range (169.254.0.0/16) covers the AWS/Azure/GCP/Oracle/
# Hetzner/DigitalOcean IMDS endpoint at 169.254.169.254 — those are blocked
# implicitly by :attr:`ipaddress.IPv4Address.is_link_local`. Alibaba Cloud
# diverges and exposes metadata on 100.100.100.200, inside the carrier-grade
# NAT range (100.64.0.0/10), which neither :attr:`is_private` nor
# :attr:`is_reserved` covers — the address space is shared-address per RFC
# 6598, not private per RFC 1918. We add it (and the surrounding /10) to an
# explicit blocklist so the validator rejects it regardless of the
# ``allow_localhost`` development override.

CLOUD_METADATA_IPV4: Final[FrozenSet[ipaddress.IPv4Network]] = frozenset(
    {
        ipaddress.IPv4Network("169.254.169.254/32"),  # AWS / Azure / GCP / Oracle / Hetzner / DO IMDS
        ipaddress.IPv4Network("100.100.100.200/32"),  # Alibaba Cloud metadata
        ipaddress.IPv4Network("100.64.0.0/10"),       # RFC 6598 carrier-grade NAT (shared address)
    }
)

CLOUD_METADATA_IPV6: Final[FrozenSet[ipaddress.IPv6Network]] = frozenset(
    {
        ipaddress.IPv6Network("fd00:ec2::254/128"),   # AWS IMDSv6
    }
)


# ---------------------------------------------------------------------------
# Path validation
# ---------------------------------------------------------------------------


_FORBIDDEN_PATH_CHARS: Final[Tuple[str, ...]] = ("\x00", "\r", "\n")


def validate_path(
    user_path: Union[str, os.PathLike[str]],
    base_dir: Union[str, os.PathLike[str]],
    *,
    allow_create: bool = False,
    follow_symlinks: bool = True,
) -> Path:
    """Validate that ``user_path`` resolves to a location within ``base_dir``.

    Canonicalises both inputs (resolving ``..`` segments and, by default,
    following symlinks) before checking containment with
    :meth:`pathlib.PurePath.is_relative_to`. String-prefix tricks like
    ``/tmp/base`` vs ``/tmp/base-evil`` are therefore rejected; raw byte
    smuggling via ``\\x00``/``\\r``/``\\n`` characters is also refused
    because those routinely confuse downstream consumers (shell, JSON
    decoders, log parsers).

    Args:
        user_path: Untrusted path. May be relative (joined onto ``base_dir``)
            or absolute (validated as-is).
        base_dir: Trusted base directory. Resolved to an absolute, canonical
            form before the containment check.
        allow_create: When ``False`` (default) the target must already
            exist; ``True`` permits the target to be missing as long as
            its parent directory exists inside ``base_dir``.
        follow_symlinks: When ``True`` (default) resolves symlinks before
            checking — protects against attackers who replace a file with
            a symlink to ``/etc/passwd``. When ``False``, the path is
            normalised without dereferencing symlinks (useful for callers
            who want to *write* the file and don't want symlink races).

    Returns:
        The canonical :class:`~pathlib.Path` inside ``base_dir``.

    Raises:
        PathValidationError: If the target sits outside ``base_dir`` or the
            input contains forbidden control bytes.
        FileNotFoundError: If the target doesn't exist and
            ``allow_create=False``.
    """
    raw = os.fspath(user_path)
    for ch in _FORBIDDEN_PATH_CHARS:
        if ch in raw:
            raise PathValidationError(
                f"Path contains forbidden control byte: {raw!r}"
            )

    base = Path(base_dir).expanduser().resolve(strict=False)

    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = base / candidate

    target = candidate.resolve(strict=False) if follow_symlinks else _normpath(candidate)

    if not _is_within(target, base):
        raise PathValidationError(
            f"Path traversal blocked: {raw!r} escapes {os.fspath(base_dir)!r}"
        )

    if not allow_create and not target.exists():
        raise FileNotFoundError(f"Path not found: {raw!r}")

    if allow_create and not target.exists():
        # Even with allow_create the parent must already be reachable
        # within the base — otherwise a writer would silently create a
        # directory in an attacker-controlled spot via a dangling
        # symlinked parent.
        parent_resolved = target.parent.resolve(strict=False) if follow_symlinks else _normpath(target.parent)
        if not _is_within(parent_resolved, base):
            raise PathValidationError(
                f"Path traversal blocked: parent of {raw!r} escapes {os.fspath(base_dir)!r}"
            )

    return target


def _normpath(p: Path) -> Path:
    """Normalise ``p`` (collapse ``..``) without following symlinks."""
    return Path(os.path.normpath(str(p)))


def _is_within(target: Path, base: Path) -> bool:
    """Return True when ``target`` is ``base`` or a descendant of it.

    Uses :meth:`PurePath.is_relative_to` on Python 3.9+; falls back to a
    canonical-component comparison if that API is missing.
    """
    if hasattr(Path, "is_relative_to"):
        try:
            return target == base or target.is_relative_to(base)
        except ValueError:
            return False
    try:
        target.relative_to(base)
        return True
    except ValueError:
        return target == base


# ---------------------------------------------------------------------------
# URL validation
# ---------------------------------------------------------------------------


_ALLOWED_SCHEMES: Final[FrozenSet[str]] = frozenset({"http", "https"})


def is_safe_url(
    url: str,
    *,
    allow_localhost: bool = False,
    allow_schemes: Optional[FrozenSet[str]] = None,
) -> bool:
    """Return True when ``url`` is safe to fetch over the network.

    Equivalent to a ``try``-wrapped :func:`assert_safe_url` — convenient
    when you want a predicate rather than an exception. Refer to
    :func:`assert_safe_url` for the validation contract.
    """
    try:
        assert_safe_url(url, allow_localhost=allow_localhost, allow_schemes=allow_schemes)
    except URLValidationError:
        return False
    return True


def assert_safe_url(
    url: str,
    *,
    allow_localhost: bool = False,
    allow_schemes: Optional[FrozenSet[str]] = None,
) -> None:
    """Reject ``url`` if it would expose us to SSRF.

    Validation steps in order:

    1. Parse the URL; reject empty/non-string input.
    2. Reject any scheme other than http/https (override via ``allow_schemes``).
    3. Reject hostnames missing from the URL.
    4. Resolve the hostname via :func:`socket.getaddrinfo`. If resolution
       fails outright the URL is rejected (a non-resolvable host on a
       fetch path is almost always a typo or an attempted injection).
    5. For every resolved address, reject loopback / link-local /
       multicast / unspecified / reserved / private addresses unless
       ``allow_localhost`` is enabled. **Cloud metadata endpoints are
       blocked regardless** to prevent leaking instance credentials.

    Args:
        url: Candidate URL.
        allow_localhost: When True, loopback (``127.0.0.0/8``, ``::1``)
            and private/reserved ranges are permitted. The cloud-metadata
            blocklist still applies.
        allow_schemes: Override the default ``{"http", "https"}`` set.
            Pass ``frozenset({"http", "https", "ws", "wss"})`` to permit
            websocket URLs, for example.

    Raises:
        URLValidationError: With a human-readable explanation of which
            rule the URL fell foul of.
    """
    if not isinstance(url, str) or not url:
        raise URLValidationError("URL must be a non-empty string")

    schemes = allow_schemes if allow_schemes is not None else _ALLOWED_SCHEMES

    try:
        parsed = urlparse(url)
    except (TypeError, ValueError) as exc:
        raise URLValidationError(f"Malformed URL: {exc}") from exc

    if parsed.scheme.lower() not in schemes:
        raise URLValidationError(
            f"Disallowed scheme {parsed.scheme!r} (allowed: {sorted(schemes)})"
        )

    hostname = parsed.hostname
    if not hostname:
        raise URLValidationError("URL has no hostname")

    # IPv6 hostnames arrive without surrounding brackets from urlparse, so
    # we can pass them straight to ipaddress / getaddrinfo. Strip a stray
    # trailing dot before resolution (DNS-legal but breaks getaddrinfo on
    # some platforms).
    hostname = hostname.rstrip(".").lower()

    if not allow_localhost:
        if hostname in {"localhost"} or hostname.endswith(".local") or hostname.endswith(".localhost"):
            raise URLValidationError(
                f"Hostname {hostname!r} resolves to local-only address space"
            )

    # If the hostname is already an IP literal, validate it directly. This
    # short-circuits DNS lookups for IP-only URLs (faster + works in
    # offline test environments) and removes a class of DNS-rebinding
    # confusion where the literal would be allowed but the lookup wouldn't.
    direct_ip = _parse_ip_literal(hostname)
    addresses: Tuple[ipaddress._BaseAddress, ...]
    if direct_ip is not None:
        addresses = (direct_ip,)
    else:
        try:
            resolved = socket.getaddrinfo(
                hostname,
                None,
                family=socket.AF_UNSPEC,
                type=socket.SOCK_STREAM,
            )
        except socket.gaierror as exc:
            raise URLValidationError(
                f"Could not resolve hostname {hostname!r}: {exc}"
            ) from exc
        try:
            addresses = tuple(
                ipaddress.ip_address(entry[4][0].split("%", 1)[0])
                for entry in resolved
            )
        except (ValueError, IndexError) as exc:
            raise URLValidationError(
                f"Hostname {hostname!r} resolved to malformed address: {exc}"
            ) from exc

    for ip in addresses:
        _enforce_address_policy(ip, hostname=hostname, allow_localhost=allow_localhost)


def _parse_ip_literal(hostname: str) -> Optional[ipaddress._BaseAddress]:
    """Return the parsed IP when ``hostname`` is a literal, otherwise ``None``."""
    try:
        return ipaddress.ip_address(hostname)
    except ValueError:
        return None


def _enforce_address_policy(
    ip: ipaddress._BaseAddress,
    *,
    hostname: str,
    allow_localhost: bool,
) -> None:
    """Raise :class:`URLValidationError` when ``ip`` violates the SSRF policy."""

    # Cloud metadata endpoints are always rejected — even when the caller
    # opts into ``allow_localhost`` for dev work. Otherwise a developer
    # using ``--allow-localhost`` on EC2 could exfiltrate the instance
    # role credentials through any tool that calls our validator.
    if isinstance(ip, ipaddress.IPv4Address):
        for net in CLOUD_METADATA_IPV4:
            if ip in net:
                raise URLValidationError(
                    f"Hostname {hostname!r} resolves to cloud-metadata "
                    f"address {ip} (network {net})"
                )
    elif isinstance(ip, ipaddress.IPv6Address):
        for net in CLOUD_METADATA_IPV6:
            if ip in net:
                raise URLValidationError(
                    f"Hostname {hostname!r} resolves to cloud-metadata "
                    f"address {ip} (network {net})"
                )

    if ip.is_unspecified:
        raise URLValidationError(
            f"Hostname {hostname!r} resolves to unspecified address {ip}"
        )
    if ip.is_multicast:
        raise URLValidationError(
            f"Hostname {hostname!r} resolves to multicast address {ip}"
        )

    if allow_localhost:
        return

    # 169.254.0.0/16 and fe80::/10 (link-local) — also catches the IPv4
    # IMDS at 169.254.169.254. Cloud metadata above is the explicit
    # override for cases where this category is permitted by mistake.
    if ip.is_loopback:
        raise URLValidationError(
            f"Hostname {hostname!r} resolves to loopback address {ip}"
        )
    if ip.is_link_local:
        raise URLValidationError(
            f"Hostname {hostname!r} resolves to link-local address {ip}"
        )
    if ip.is_private:
        raise URLValidationError(
            f"Hostname {hostname!r} resolves to private address {ip}"
        )
    if ip.is_reserved:
        raise URLValidationError(
            f"Hostname {hostname!r} resolves to reserved address {ip}"
        )
