"""Reject URLs that point at private, loopback, or local targets."""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit

BLOCKED_HOSTNAMES = {"localhost", "metadata.google.internal"}
ALLOWED_SCHEMES = {"http", "https"}


class UnsafeUrl(ValueError):
    """A URL that the research fetcher must not contact."""


def _is_blocked_ip(value: str) -> bool:
    ip = ipaddress.ip_address(value)
    return (
        ip.is_private or ip.is_loopback or ip.is_link_local
        or ip.is_multicast or ip.is_reserved or ip.is_unspecified
    )


def assert_safe_url(url: str) -> str:
    """Return the URL when it is safe. Raise UnsafeUrl otherwise."""
    parts = urlsplit(url)
    if parts.scheme not in ALLOWED_SCHEMES:
        raise UnsafeUrl("SCHEME_NOT_ALLOWED")
    if parts.username or parts.password:
        raise UnsafeUrl("CREDENTIALS_IN_URL")
    host = (parts.hostname or "").rstrip(".").lower()
    if not host or host in BLOCKED_HOSTNAMES:
        raise UnsafeUrl("HOST_NOT_ALLOWED")

    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        if _is_blocked_ip(str(literal)):
            raise UnsafeUrl("PRIVATE_ADDRESS")
        return url

    try:
        infos = socket.getaddrinfo(
            host,
            parts.port or (443 if parts.scheme == "https" else 80),
            proto=socket.IPPROTO_TCP,
        )
    except socket.gaierror as exc:
        raise UnsafeUrl("DNS_FAILED") from exc
    for info in infos:
        if _is_blocked_ip(str(info[4][0])):
            raise UnsafeUrl("PRIVATE_ADDRESS")
    return url
