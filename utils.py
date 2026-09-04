# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Shared utility functions for xavani-agent."""

import json
import logging
import os
import stat
import tempfile
from pathlib import Path
from typing import Any, Union
from urllib.parse import urlparse

import yaml

logger = logging.getLogger(__name__)


TRUTHY_STRINGS = frozenset({"1", "true", "yes", "on"})


def is_truthy_value(value: Any, default: bool = False) -> bool:
    """Coerce bool-ish values using the project's shared truthy string set."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in TRUTHY_STRINGS
    return bool(value)


def env_var_enabled(name: str, default: str = "") -> bool:
    """Return True when an environment variable is set to a truthy value."""
    return is_truthy_value(os.getenv(name, default), default=False)


def _preserve_file_mode(path: Path) -> "int | None":
    """Capture the permission bits of *path* if it exists, else ``None``."""
    try:
        return stat.S_IMODE(path.stat().st_mode) if path.exists() else None
    except OSError:
        return None


def _restore_file_mode(path: Path, mode: "int | None") -> None:
    """Re-apply *mode* to *path* after an atomic replace.

    ``tempfile.mkstemp`` creates files with 0o600 (owner-only).  After
    ``os.replace`` swaps the temp file into place the target inherits
    those restrictive permissions, breaking Docker / NAS volume mounts
    that rely on broader permissions set by the user.  Calling this
    right after ``os.replace`` restores the original permissions.
    """
    if mode is None:
        return
    try:
        os.chmod(path, mode)
    except OSError:
        pass


def atomic_replace(tmp_path: Union[str, Path], target: Union[str, Path]) -> str:
    """Atomically move *tmp_path* onto *target*, preserving symlinks.

    ``os.replace(tmp, target)`` atomically swaps ``tmp`` into place at
    ``target``.  When ``target`` is a symlink, the symlink itself is
    replaced with a regular file — silently detaching managed deployments
    that symlink ``config.yaml`` / ``SOUL.md`` / ``auth.json`` etc. from
    ``~/.xavani/`` to a git-tracked profile package or dotfiles repo
    (GitHub #16743).

    This helper resolves the symlink first so ``os.replace`` writes to
    the real file in-place while the symlink survives.  For non-symlink
    and non-existent paths the behavior is identical to a plain
    ``os.replace`` call.

    Returns the resolved real path used for the replace, so callers that
    need to re-apply permissions can target it instead of the symlink.
    """
    target_str = str(target)
    real_path = os.path.realpath(target_str) if os.path.islink(target_str) else target_str
    os.replace(str(tmp_path), real_path)
    return real_path


def atomic_json_write(
    path: Union[str, Path],
    data: Any,
    *,
    indent: int = 2,
    **dump_kwargs: Any,
) -> None:
    """Write JSON data to a file atomically.

    Uses temp file + fsync + os.replace to ensure the target file is never
    left in a partially-written state. If the process crashes mid-write,
    the previous version of the file remains intact.

    Args:
        path: Target file path (will be created or overwritten).
        data: JSON-serializable data to write.
        indent: JSON indentation (default 2).
        **dump_kwargs: Additional keyword args forwarded to json.dump(), such
            as default=str for non-native types.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    original_mode = _preserve_file_mode(path)

    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f".{path.stem}_",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                indent=indent,
                ensure_ascii=False,
                **dump_kwargs,
            )
            f.flush()
            os.fsync(f.fileno())
        # Preserve symlinks — swap in-place on the real file (GitHub #16743).
        real_path = atomic_replace(tmp_path, path)
        _restore_file_mode(real_path, original_mode)
    except BaseException:
        # Intentionally catch BaseException so temp-file cleanup still runs for
        # KeyboardInterrupt/SystemExit before re-raising the original signal.
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def atomic_yaml_write(
    path: Union[str, Path],
    data: Any,
    *,
    default_flow_style: bool = False,
    sort_keys: bool = False,
    extra_content: str | None = None,
) -> None:
    """Write YAML data to a file atomically.

    Uses temp file + fsync + os.replace to ensure the target file is never
    left in a partially-written state.  If the process crashes mid-write,
    the previous version of the file remains intact.

    Args:
        path: Target file path (will be created or overwritten).
        data: YAML-serializable data to write.
        default_flow_style: YAML flow style (default False).
        sort_keys: Whether to sort dict keys (default False).
        extra_content: Optional string to append after the YAML dump
            (e.g. commented-out sections for user reference).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    original_mode = _preserve_file_mode(path)

    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f".{path.stem}_",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=default_flow_style, sort_keys=sort_keys)
            if extra_content:
                f.write(extra_content)
            f.flush()
            os.fsync(f.fileno())
        # Preserve symlinks — swap in-place on the real file (GitHub #16743).
        real_path = atomic_replace(tmp_path, path)
        _restore_file_mode(real_path, original_mode)
    except BaseException:
        # Match atomic_json_write: cleanup must also happen for process-level
        # interruptions before we re-raise them.
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def atomic_roundtrip_yaml_update(
    path: Union[str, Path],
    key_path: str,
    value: Any,
) -> None:
    """Update one dotted YAML key while preserving comments and readable text.

    This is intentionally narrower than :func:`atomic_yaml_write`: it is for
    user-edited config files where comments, ordering, quoting, and Unicode
    should survive a single setting mutation.  Writes still use the same temp
    file + fsync + atomic replace pattern.
    """
    from ruamel.yaml import YAML
    from ruamel.yaml.comments import CommentedMap

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    yaml_rt = YAML(typ="rt")
    yaml_rt.preserve_quotes = True
    yaml_rt.allow_unicode = True
    yaml_rt.default_flow_style = False
    yaml_rt.indent(mapping=2, sequence=4, offset=2)

    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            config = yaml_rt.load(f) or CommentedMap()
    else:
        config = CommentedMap()

    if not isinstance(config, CommentedMap):
        config = CommentedMap(config)

    current = config
    keys = key_path.split(".")
    for key in keys[:-1]:
        next_value = current.get(key)
        if not isinstance(next_value, CommentedMap):
            next_value = CommentedMap()
            current[key] = next_value
        current = next_value
    current[keys[-1]] = value

    original_mode = _preserve_file_mode(path)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f".{path.stem}_",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            yaml_rt.dump(config, f)
            f.flush()
            os.fsync(f.fileno())
        real_path = atomic_replace(tmp_path, path)
        _restore_file_mode(real_path, original_mode)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ─── JSON Helpers ─────────────────────────────────────────────────────────────


def safe_json_loads(text: str, default: Any = None) -> Any:
    """Parse JSON, returning *default* on any parse error.

    Replaces the ``try: json.loads(x) except (JSONDecodeError, TypeError)``
    pattern duplicated across display.py, anthropic_adapter.py,
    auxiliary_client.py, and others.
    """
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError, ValueError):
        return default


# ─── Environment Variable Helpers ─────────────────────────────────────────────


def env_int(key: str, default: int = 0) -> int:
    """Read an environment variable as an integer, with fallback."""
    raw = os.getenv(key, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except (ValueError, TypeError):
        return default


def env_bool(key: str, default: bool = False) -> bool:
    """Read an environment variable as a boolean."""
    return is_truthy_value(os.getenv(key, ""), default=default)


# ─── Proxy Helpers ────────────────────────────────────────────────────────────


_PROXY_ENV_KEYS = (
    "HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY",
    "https_proxy", "http_proxy", "all_proxy",
)


def normalize_proxy_url(proxy_url: str | None) -> str | None:
    """Normalize proxy URLs for httpx/aiohttp compatibility.

    WSL/Clash-style environments often export SOCKS proxies as
    ``socks://127.0.0.1:PORT``. httpx rejects that alias and expects the
    explicit ``socks5://`` scheme instead.
    """
    candidate = str(proxy_url or "").strip()
    if not candidate:
        return None
    if candidate.lower().startswith("socks://"):
        return f"socks5://{candidate[len('socks://'):]}"
    return candidate


def normalize_proxy_env_vars() -> None:
    """Rewrite supported proxy env vars to canonical URL forms in-place."""
    for key in _PROXY_ENV_KEYS:
        value = os.getenv(key, "")
        normalized = normalize_proxy_url(value)
        if normalized and normalized != value:
            os.environ[key] = normalized


# ─── URL Parsing Helpers ──────────────────────────────────────────────────────


def base_url_hostname(base_url: str) -> str:
    """Return the lowercased hostname for a base URL, or ``""`` if absent.

    Use exact-hostname comparisons against known provider hosts
    (``api.openai.com``, ``api.x.ai``, ``api.anthropic.com``) instead of
    substring matches on the raw URL. Substring checks treat attacker- or
    proxy-controlled paths/hosts like ``https://api.openai.com.example/v1``
    or ``https://proxy.test/api.openai.com/v1`` as native endpoints, which
    leads to wrong api_mode / auth routing.
    """
    raw = (base_url or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw if "://" in raw else f"//{raw}")
    return (parsed.hostname or "").lower().rstrip(".")


def base_url_host_matches(base_url: str, domain: str) -> bool:
    """Return True when the base URL's hostname is ``domain`` or a subdomain.

    Safer counterpart to ``domain in base_url``, which is the substring
    false-positive class documented on ``base_url_hostname``. Accepts bare
    hosts, full URLs, and URLs with paths.

        base_url_host_matches("https://api.moonshot.ai/v1", "moonshot.ai") == True
        base_url_host_matches("https://moonshot.ai", "moonshot.ai")        == True
        base_url_host_matches("https://evil.com/moonshot.ai/v1", "moonshot.ai") == False
        base_url_host_matches("https://moonshot.ai.evil/v1", "moonshot.ai")     == False
    """
    hostname = base_url_hostname(base_url)
    if not hostname:
        return False
    domain = (domain or "").strip().lower().rstrip(".")
    if not domain:
        return False
    return hostname == domain or hostname.endswith("." + domain)


def _preserve_file_owner(path: Path) -> "tuple[int, int] | None":
    """Capture the owning uid/gid of *path* if the platform supports it."""
    if os.name != "posix":
        return None
    try:
        st = path.stat()
    except OSError:
        return None
    return st.st_uid, st.st_gid


def _restore_file_owner(path: Path, owner: "tuple[int, int] | None") -> None:
    """Re-apply uid/gid after an atomic replace when permitted.

    Docker and NAS-backed installs often run some commands as root while the
    persistent volume is owned by the runtime user. ``os.replace`` swaps in the
    temp file's owner, so a root-run config write can leave ``config.yaml`` owned
    by root. Best-effort chown preserves the existing owner for privileged
    callers and is harmless for unprivileged callers that cannot chown.
    """
    if owner is None or not hasattr(os, "chown"):
        return
    try:
        os.chown(path, owner[0], owner[1])
    except OSError:
        pass


def atomic_write_text(
    path: Union[str, Path],
    content: str,
    *,
    encoding: str = "utf-8",
    tmp_prefix: str = ".tmp_",
    preserve_mode: bool = False,
    create_mode: "int | None" = None,
) -> None:
    """Write *content* to *path* via temp file + fsync + atomic rename.

    Ensures the target file is never left in a partially-written state if
    the process crashes or is interrupted.  ``atomic_replace`` preserves
    symlinks and handles cross-device / busy-file fallbacks.

    Used by the memory store, skill manager, and agent importer so that
    every destructive file rewrite in the codebase shares one implementation.

    Args:
        preserve_mode: When True, carry an existing target's permission bits
            and (POSIX, best-effort) owner across the replace, like
            ``atomic_yaml_write`` does unconditionally.  ``os.replace`` swaps
            in mkstemp's 0600 temp file owned by the writing user, so without
            this a root-run rewrite of a user-owned file flips its owner and
            tightens its mode.  The mode is applied to the temp fd *before*
            the replace, so the file never transits through 0600.  Off by
            default: the historical callers (memory store, skill manager,
            cron) own their 0600-is-fine files.
        create_mode: Permission bits to apply when the target does not yet
            exist (otherwise the new file keeps mkstemp's 0600).  Never
            applied to an existing file.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    original_mode = _preserve_file_mode(path) if preserve_mode else None
    original_owner = _preserve_file_owner(path) if preserve_mode else None
    effective_mode = original_mode
    if effective_mode is None and create_mode is not None and not path.exists():
        effective_mode = create_mode

    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent), prefix=tmp_prefix, suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding=encoding) as handle:
            if effective_mode is not None and hasattr(os, "fchmod"):
                os.fchmod(handle.fileno(), effective_mode)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        real_path = atomic_replace(tmp_path, path)
        if preserve_mode:
            _restore_file_owner(Path(real_path), original_owner)
        if effective_mode is not None and not hasattr(os, "fchmod"):
            _restore_file_mode(Path(real_path), effective_mode)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


_fast_yaml_loader = None


def _get_fast_yaml_loader():
    global _fast_yaml_loader
    if _fast_yaml_loader is None:
        _fast_yaml_loader = getattr(yaml, "CSafeLoader", None) or yaml.SafeLoader
    return _fast_yaml_loader


def fast_safe_load(stream: Any) -> Any:
    """``yaml.safe_load`` using the libyaml C loader when available.

    Accepts the same inputs as ``yaml.safe_load`` (a ``str``/``bytes`` document
    or a readable file object) and returns the same parsed structure. Falls
    back to PyYAML's pure-Python ``SafeLoader`` when ``CSafeLoader`` isn't
    available, so behavior is identical everywhere — only the speed differs.
    """
    return yaml.load(stream, Loader=_get_fast_yaml_loader())
