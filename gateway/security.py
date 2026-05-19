# Copyright (c) 2025-2026 Enternovate. All rights reserved.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Security utilities for path validation and URL safety."""

from pathlib import Path
import os


# Directories that are always allowed as base paths
_TRUSTED_BASES: dict[str, Path] = {}


def validate_path(user_path: str, base_dir: str | Path, *, allow_create: bool = False) -> Path:
    """Validate that user_path resolves to a location within base_dir.
    
    Prevents path traversal attacks by resolving both paths and checking
    the resolved user path starts with the resolved base directory.
    
    Args:
        user_path: Untrusted path string from user input.
        base_dir: Trusted base directory that paths must stay within.
        allow_create: If True, don't require the target file to already exist.
    
    Returns:
        Resolved Path object within base_dir.
    
    Raises:
        ValueError: If the path would escape base_dir.
        FileNotFoundError: If the path doesn't exist and allow_create is False.
    """
    base = Path(base_dir).resolve()
    target = (base / user_path).resolve() if not os.path.isabs(user_path) else Path(user_path).resolve()
    
    if not str(target).startswith(str(base) + os.sep) and target != base:
        raise ValueError(f"Path traversal blocked: {user_path!r} escapes {base_dir}")
    
    if not allow_create and not target.exists():
        raise FileNotFoundError(f"Path not found: {user_path!r}")
    
    return target


def is_safe_url(url: str, *, allow_localhost: bool = False) -> bool:
    """Check if a URL is safe to fetch (blocks SSRF attacks).
    
    Rejects non-HTTP(S) schemes, internal/private network hosts,
    and (unless allow_localhost=True) localhost/loopback addresses.
    """
    from urllib.parse import urlparse
    import ipaddress
    import socket
    
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    
    if parsed.scheme not in ("http", "https"):
        return False
    
    hostname = parsed.hostname
    if not hostname:
        return False
    
    if not allow_localhost:
        if hostname in ("localhost", "127.0.0.1", "::1") or hostname.endswith(".local"):
            return False
    
    try:
        resolved = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for entry in resolved:
            addr = entry[4][0]
            ip = ipaddress.ip_address(addr)
            if not allow_localhost and (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved):
                return False
    except (socket.gaierror, ValueError):
        pass
    
    return True