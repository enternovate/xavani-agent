# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""XAVANI_HOME filesystem validation (A18).

Verifies the home directory is safe for persistent state before the
agent starts. Checks run at entry-point startup (xavani.py / cli.py):

- writable
- free space above the minimum (50 MB)
- file locking works (flock on POSIX, LockFileEx on Windows)
- not a symlink to a network mount
- not inside a Docker volume backed by NFS

A bad home silently corrupts session DBs and config. These checks turn
that into a loud, actionable error at startup. Never raises — reports
problems as a list of strings so the caller decides the exit policy.

Set XAVANI_SKIP_HOME_CHECK=1 to disable (e.g. unusual FUSE mounts
where flock semantics differ and the operator accepts the risk).
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

_MIN_FREE_BYTES = 50 * 1024 * 1024  # 50 MB

# Filesystems that do not provide reliable POSIX locking semantics.
# Docker volumes backed by these (e.g. ``-v myvol:/root/.xavani`` where
# the volume driver is NFS) silently break session locking.
_UNLOCKED_FS_TYPES = frozenset(
    {
        "nfs",
        "nfs4",
        "cifs",
        "smbfs",
        "smb3",
        "sshfs",
        "fuse.sshfs",
        "9p",
        "davfs",
        "davfs2",
        "fuse.davfs2",
        "lustre",
        "gpfs",
        "ceph",
        "fuse.ceph",
    }
)

# Cache: resolved-home -> list of problems (immutable per process).
_home_check_cache: dict[str, tuple[str, ...]] = {}


def _is_windows() -> bool:
    return sys.platform == "win32"


# Mount table (mountpoint, fstype), parsed once per process. The mount
# table is effectively static for a process lifetime; caching avoids a
# `mount` subprocess (macOS) or /proc/mounts re-read (Linux) on every
# cli.main() call with a fresh XAVANI_HOME (tests, subprocess spawns).
_mount_table_cache: tuple[tuple[str, str], ...] | None = None


def _load_mount_table() -> tuple[tuple[str, str], ...]:
    """Parse the mount table into (mountpoint, fstype) pairs, cached."""
    global _mount_table_cache
    if _mount_table_cache is not None:
        return _mount_table_cache

    table: list[tuple[str, str]] = []
    if not _is_windows():
        try:
            with open("/proc/mounts", encoding="utf-8") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 3:
                        table.append((parts[1], parts[2]))
        except OSError:
            pass
        if not table:
            # macOS fallback: parse `mount` output lines like
            # "/dev/disk1s1 on / (apfs, local, journaled)".
            try:
                import subprocess

                out = subprocess.run(
                    ["mount"],
                    capture_output=True,
                    text=True,
                    timeout=3,
                    check=False,
                ).stdout
                for line in out.splitlines():
                    parts = line.split(" on ")
                    if len(parts) < 2:
                        continue
                    mountpoint = parts[1].split(" ")[0]
                    rest = line.rsplit("(", 1)
                    fstype = rest[1].split(",")[0].strip().rstrip(")") if len(rest) == 2 else ""
                    table.append((mountpoint, fstype))
            except Exception:
                pass
    _mount_table_cache = tuple(table)
    return _mount_table_cache


def _fs_type(path: Path) -> str:
    """Return the filesystem type hosting ``path``, or \"\" when unknown.

    Matches the mount whose target is the longest prefix of the path.
    """
    try:
        resolved = str(path.resolve())
    except OSError:
        resolved = str(path)
    best = ("", "")
    for mountpoint, fstype in _load_mount_table():
        if mountpoint == "/" or resolved.startswith(mountpoint):
            if len(mountpoint) > len(best[1]):
                best = (fstype, mountpoint)
    return best[0]


def _lockable(path: Path) -> bool:
    """Probe file locking with a real exclusive lock on a scratch file."""
    probe = path / ".xavani_lock_probe"
    try:
        with open(probe, "wb") as f:
            if _is_windows():
                import msvcrt

                lock_fn = getattr(msvcrt, "locking", None)
                if lock_fn is None:
                    return False
                f.write(b"lock")
                f.flush()
                try:
                    lock_fn(f.fileno(), getattr(msvcrt, "LK_NBLCK", 1), 1)
                except OSError:
                    return False
                try:
                    f.seek(0)
                    lock_fn(f.fileno(), getattr(msvcrt, "LK_UNLCK", 0), 1)
                except OSError:
                    pass
            else:
                import fcntl

                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        return True
    except (OSError, ImportError):
        return False
    finally:
        try:
            probe.unlink()
        except OSError:
            pass


def _writable(path: Path) -> bool:
    """Probe write access with a real file create/delete (not just stat)."""
    probe = path / ".xavani_write_probe"
    try:
        with open(probe, "wb") as f:
            f.write(b"probe")
        probe.unlink()
        return True
    except OSError:
        return False


def check_xavani_home(home: Path | None = None) -> list[str]:
    """Validate a Xavani home directory. Returns a list of problems.

    An empty list means the home is healthy. Each entry names the failed
    check and the action to take. Results are cached per resolved path.
    """
    path = Path(home) if home is not None else Path(os.environ.get("XAVANI_HOME", "") or "~/.xavani")
    try:
        key = str(path.resolve())
    except OSError:
        key = str(path)
    if key in _home_check_cache:
        return list(_home_check_cache[key])

    problems: list[str] = []
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        problems.append(
            f"XAVANI_HOME {path} cannot be created: {exc}. "
            f"Create it with write permission for the current user."
        )
        _home_check_cache[key] = tuple(problems)
        return problems

    if not path.is_dir():
        problems.append(f"XAVANI_HOME {path} is not a directory.")

    if not _writable(path):
        problems.append(
            f"XAVANI_HOME {path} is not writable. State files (session DB, "
            f"config.yaml) cannot be persisted. Fix permissions and retry."
        )

    try:
        usage = shutil.disk_usage(path)
        if usage.free < _MIN_FREE_BYTES:
            problems.append(
                f"XAVANI_HOME {path} has {usage.free // (1024 * 1024)} MB free; "
                f"minimum is {_MIN_FREE_BYTES // (1024 * 1024)} MB. "
                f"Session history and memory will corrupt under disk pressure."
            )
    except OSError:
        pass  # the writability probe already covers unusable mounts

    ftype = _fs_type(path)
    if ftype and ftype in _UNLOCKED_FS_TYPES:
        problems.append(
            f"XAVANI_HOME {path} is on a {ftype} filesystem. Network "
            f"filesystems do not provide reliable locking; session "
            f"corruption is likely. Move XAVANI_HOME to local disk "
            f"(e.g. ~/.xavani) and set XAVANI_HOME to that path."
        )
    elif not _lockable(path):
        problems.append(
            f"XAVANI_HOME {path} does not support file locking. Session "
            f"store locks will fail. Use a local filesystem and set "
            f"XAVANI_HOME to that path."
        )

    _home_check_cache[key] = tuple(problems)
    return problems


def home_check_enabled() -> bool:
    """True when the startup home check is enabled (default)."""
    return os.environ.get("XAVANI_SKIP_HOME_CHECK") != "1"


def report_home_problems(home: Path | None = None, *, stream=None) -> list[str]:
    """Run the check and print each problem to stderr.

    Returns the problems (for the caller's exit policy). Prints nothing
    when the home is healthy or the check is disabled.
    """
    if not home_check_enabled():
        return []
    problems = check_xavani_home(home)
    if not problems:
        return []
    out = stream or sys.stderr
    for msg in problems:
        try:
            out.write(f"⚠️  xavani home: {msg}\n")
            out.flush()
        except Exception:
            pass
    return problems


def clear_home_check_cache() -> None:
    """Clear the cached check results and mount table. For tests."""
    global _mount_table_cache
    _home_check_cache.clear()
    _mount_table_cache = None
