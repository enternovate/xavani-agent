# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""
Backup and import commands for xavani CLI.

`xavani backup` creates a zip archive of the entire ~/.xavani/ directory
(excluding the xavani-agent repo and transient files).

`xavani import` restores from a backup zip, overlaying onto the current
XAVANI_HOME root.
"""

import json
import logging
import os
import shutil
import sqlite3
import sys
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from xavani_constants import get_default_xavani_root, get_xavani_home, display_xavani_home

logger = logging.getLogger(__name__)
try:
    from xavani_cli.safe_logging import SafeLogFilter
    SafeLogFilter.install()
except Exception:
    pass


# ---------------------------------------------------------------------------
# Exclusion rules
# ---------------------------------------------------------------------------

# Directory names to skip entirely (matched against each path component)
_EXCLUDED_DIRS = {
    "xavani-agent",     # the codebase repo — re-clone instead
    "__pycache__",      # bytecode caches — regenerated on import
    ".git",             # nested git dirs (profiles shouldn't have these, but safety)
    "node_modules",     # js deps if website/ somehow leaks in
    "backups",          # prior auto-backups — don't nest backups exponentially
    "checkpoints",      # session-local trajectory caches — regenerated per-session,
                        # session-hash-keyed so they don't port to another machine anyway
}

# File-name suffixes to skip
_EXCLUDED_SUFFIXES = (
    ".pyc",
    ".pyo",
    # SQLite sidecar files — the backup takes a consistent snapshot of ``*.db``
    # via ``sqlite3.backup()``, so shipping the live WAL / shared-memory /
    # rollback-journal alongside would pair a fresh snapshot with stale sidecar
    # state and produce a torn restore on the next open. They're transient and
    # regenerated on first connection anyway.
    ".db-wal",
    ".db-shm",
    ".db-journal",
)

# File names to skip (runtime state that's meaningless on another machine)
_EXCLUDED_NAMES = {
    "gateway.pid",
    "cron.pid",
}

# zipfile.open() drops Unix mode bits on extract; restore tightens these to 0600.
_SECRET_FILE_NAMES = {".env", "auth.json", "state.db"}


def _should_exclude(rel_path: Path) -> bool:
    """Return True if *rel_path* (relative to xavani root) should be skipped."""
    parts = rel_path.parts

    # Any path component matches an excluded dir name
    for part in parts:
        if part in _EXCLUDED_DIRS:
            return True

    name = rel_path.name

    if name in _EXCLUDED_NAMES:
        return True

    if name.endswith(_EXCLUDED_SUFFIXES):
        return True

    return False


# ---------------------------------------------------------------------------
# SQLite safe copy
# ---------------------------------------------------------------------------

def _safe_copy_db(src: Path, dst: Path) -> bool:
    """Copy a SQLite database safely using the backup() API.

    Handles WAL mode — produces a consistent snapshot even while
    the DB is being written to.  Falls back to raw copy on failure.
    """
    try:
        conn = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
        backup_conn = sqlite3.connect(str(dst))
        conn.backup(backup_conn)
        backup_conn.close()
        conn.close()
        return True
    except Exception as exc:
        logger.warning("SQLite safe copy failed for %s: %s", src, exc)
        try:
            shutil.copy2(src, dst)
            return True
        except Exception as exc2:
            logger.error("Raw copy also failed for %s: %s", src, exc2)
            return False


# ---------------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------------

def _format_size(nbytes: int) -> str:
    """Human-readable file size."""
    for unit in ("B", "KB", "MB", "GB"):
        if nbytes < 1024:
            return f"{nbytes:.1f} {unit}" if unit != "B" else f"{nbytes} {unit}"
        nbytes /= 1024
    return f"{nbytes:.1f} TB"


def run_backup(args) -> None:
    """Create a zip backup of the Xavani home directory."""
    xavani_root = get_default_xavani_root()

    if not xavani_root.is_dir():
        print(f"Error: Xavani home directory not found at {xavani_root}")
        sys.exit(1)

    # Determine output path
    if args.output:
        out_path = Path(args.output).expanduser().resolve()
        # Validate output path stays within expected dirs
        _home = Path.home()
        if not str(out_path).startswith(str(_home)):
            print("Error: output path must be within home directory")
            sys.exit(1)
        if out_path.is_dir():
            stamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
            out_path = out_path / f"xavani-backup-{stamp}.zip"
    else:
        stamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        out_path = Path.home() / f"xavani-backup-{stamp}.zip"

    # Ensure the suffix is .zip
    if out_path.suffix.lower() != ".zip":
        out_path = out_path.with_suffix(out_path.suffix + ".zip")

    # Ensure parent directory exists
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Collect files
    print(f"Scanning {display_xavani_home()} ...")
    files_to_add: list[tuple[Path, Path]] = []  # (absolute, relative)
    skipped_dirs = set()

    for dirpath, dirnames, filenames in os.walk(xavani_root, followlinks=False):
        dp = Path(dirpath)
        rel_dir = dp.relative_to(xavani_root)

        # Prune excluded directories in-place so os.walk doesn't descend
        orig_dirnames = dirnames[:]
        dirnames[:] = [
            d for d in dirnames
            if d not in _EXCLUDED_DIRS
        ]
        for removed in set(orig_dirnames) - set(dirnames):
            skipped_dirs.add(str(rel_dir / removed))

        for fname in filenames:
            fpath = dp / fname
            rel = fpath.relative_to(xavani_root)

            if _should_exclude(rel):
                continue

            # Skip the output zip itself if it happens to be inside xavani root
            try:
                if fpath.resolve() == out_path.resolve():
                    continue
            except (OSError, ValueError):
                pass

            files_to_add.append((fpath, rel))

    if not files_to_add:
        print("No files to back up.")
        return

    # Create the zip
    file_count = len(files_to_add)
    print(f"Backing up {file_count} files ...")

    total_bytes = 0
    errors = []
    t0 = time.monotonic()

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for i, (abs_path, rel_path) in enumerate(files_to_add, 1):
            try:
                # Safe copy for SQLite databases (handles WAL mode)
                if abs_path.suffix == ".db":
                    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
                        tmp_db = Path(tmp.name)
                    if _safe_copy_db(abs_path, tmp_db):
                        zf.write(tmp_db, arcname=str(rel_path))
                        total_bytes += tmp_db.stat().st_size
                        tmp_db.unlink(missing_ok=True)
                    else:
                        tmp_db.unlink(missing_ok=True)
                        errors.append(f"  {rel_path}: SQLite safe copy failed")
                        continue
                else:
                    zf.write(abs_path, arcname=str(rel_path))
                    total_bytes += abs_path.stat().st_size
            except (PermissionError, OSError, ValueError) as exc:
                errors.append(f"  {rel_path}: {exc}")
                continue

            # Progress every 500 files
            if i % 500 == 0:
                print(f"  {i}/{file_count} files ...")

    elapsed = time.monotonic() - t0
    zip_size = out_path.stat().st_size

    # Summary
    print()
    print(f"Backup complete: {out_path}")
    print(f"  Files:       {file_count}")
    print(f"  Original:    {_format_size(total_bytes)}")
    print(f"  Compressed:  {_format_size(zip_size)}")
    print(f"  Time:        {elapsed:.1f}s")

    if skipped_dirs:
        print(f"\n  Excluded directories:")
        for d in sorted(skipped_dirs):
            print(f"    {d}/")

    if errors:
        print(f"\n  Warnings ({len(errors)} files skipped):")
        for e in errors[:10]:
            print(e)
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more")

    print(f"\nRestore with: xavani import {out_path.name}")


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------

def _validate_backup_zip(zf: zipfile.ZipFile) -> tuple[bool, str]:
    """Check that a zip looks like a Xavani backup.

    Returns (ok, reason).
    """
    names = zf.namelist()
    if not names:
        return False, "zip archive is empty"

    # Look for telltale files that a xavani home would have
    markers = {"config.yaml", ".env", "state.db"}
    found = set()
    for n in names:
        # Could be at the root or one level deep (if someone zipped the directory)
        basename = Path(n).name
        if basename in markers:
            found.add(basename)

    if not found:
        return False, (
            "zip does not appear to be a Xavani backup "
            "(no config.yaml, .env, or state databases found)"
        )

    return True, ""


def _detect_prefix(zf: zipfile.ZipFile) -> str:
    """Detect if the zip has a common directory prefix wrapping all entries.

    Some tools zip as `.xavani/config.yaml` instead of `config.yaml`.
    Returns the prefix to strip (empty string if none).
    """
    names = [n for n in zf.namelist() if not n.endswith("/")]
    if not names:
        return ""

    # Find common prefix
    parts_list = [Path(n).parts for n in names]

    # Check if all entries share a common first directory
    first_parts = {p[0] for p in parts_list if len(p) > 1}
    if len(first_parts) == 1:
        prefix = first_parts.pop()
        # Only strip if it looks like a xavani dir name
        if prefix in {".xavani", "xavani"}:
            return prefix + "/"

    return ""


def run_import(args) -> None:
    """Restore a Xavani backup from a zip file."""
    zip_path = Path(args.zipfile).expanduser().resolve()

    if not zip_path.is_file():
        print(f"Error: File not found: {zip_path}")
        sys.exit(1)

    if not zipfile.is_zipfile(zip_path):
        print(f"Error: Not a valid zip file: {zip_path}")
        sys.exit(1)

    xavani_root = get_default_xavani_root()

    with zipfile.ZipFile(zip_path, "r") as zf:
        # Validate
        ok, reason = _validate_backup_zip(zf)
        if not ok:
            print(f"Error: {reason}")
            sys.exit(1)

        prefix = _detect_prefix(zf)
        members = [n for n in zf.namelist() if not n.endswith("/")]
        file_count = len(members)

        print(f"Backup contains {file_count} files")
        print(f"Target: {display_xavani_home()}")

        if prefix:
            print(f"Detected archive prefix: {prefix!r} (will be stripped)")

        # Check for existing installation
        has_config = (xavani_root / "config.yaml").exists()
        has_env = (xavani_root / ".env").exists()

        if (has_config or has_env) and not args.force:
            print()
            print("Warning: Target directory already has Xavani configuration.")
            print("Importing will overwrite existing files with backup contents.")
            print()
            try:
                answer = input("Continue? [y/N] ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\nAborted.")
                sys.exit(1)
            if answer not in {"y", "yes"}:
                print("Aborted.")
                return

        # Extract
        print(f"\nImporting {file_count} files ...")
        xavani_root.mkdir(parents=True, exist_ok=True)

        errors = []
        restored = 0
        t0 = time.monotonic()

        for member in members:
            # Strip prefix if detected
            if prefix and member.startswith(prefix):
                rel = member[len(prefix):]
            else:
                rel = member

            if not rel:
                continue

            target = xavani_root / rel

            # Security: reject absolute paths and traversals
            try:
                target.resolve().relative_to(xavani_root.resolve())
            except ValueError:
                errors.append(f"  {rel}: path traversal blocked")
                continue

            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as src, open(target, "wb") as dst:
                    dst.write(src.read())
                if target.name in _SECRET_FILE_NAMES:
                    os.chmod(target, 0o600)
                restored += 1
            except (PermissionError, OSError) as exc:
                errors.append(f"  {rel}: {exc}")

            if restored % 500 == 0:
                print(f"  {restored}/{file_count} files ...")

        elapsed = time.monotonic() - t0

        # Summary
        print()
        print(f"Import complete: {restored} files restored in {elapsed:.1f}s")
        print(f"  Target: {display_xavani_home()}")

        if errors:
            print(f"\n  Warnings ({len(errors)} files skipped):")
            for e in errors[:10]:
                print(e)
            if len(errors) > 10:
                print(f"  ... and {len(errors) - 10} more")

        # Post-import: restore profile wrapper scripts
        profiles_dir = xavani_root / "profiles"
        restored_profiles = []
        if profiles_dir.is_dir():
            try:
                from xavani_cli.profiles import (
                    create_wrapper_script, check_alias_collision,
                    _is_wrapper_dir_in_path, _get_wrapper_dir,
                )
                for entry in sorted(profiles_dir.iterdir()):
                    if not entry.is_dir():
                        continue
                    profile_name = entry.name
                    # Only create wrappers for directories with config
                    if not (entry / "config.yaml").exists() and not (entry / ".env").exists():
                        continue
                    collision = check_alias_collision(profile_name)
                    if collision:
                        print(f"  Skipped alias '{profile_name}': {collision}")
                        restored_profiles.append((profile_name, False))
                    else:
                        wrapper = create_wrapper_script(profile_name)
                        restored_profiles.append((profile_name, wrapper is not None))

                if restored_profiles:
                    created = [n for n, ok in restored_profiles if ok]
                    skipped = [n for n, ok in restored_profiles if not ok]
                    if created:
                        print(f"\n  Profile aliases restored: {', '.join(created)}")
                    if skipped:
                        print(f"  Profile aliases skipped:  {', '.join(skipped)}")
                    if not _is_wrapper_dir_in_path():
                        print(f"\n  Note: {_get_wrapper_dir()} is not in your PATH.")
                        print('  Add to your shell config (~/.bashrc or ~/.zshrc):')
                        print('    export PATH="$HOME/.local/bin:$PATH"')
            except ImportError:
                # xavani_cli.profiles might not be available (fresh install)
                if any(profiles_dir.iterdir()):
                    print(f"\n  Profiles detected but aliases could not be created.")
                    print(f"  Run: xavani profile list  (after installing xavani)")

        # Guidance
        print()
        if not (xavani_root / "xavani-agent").is_dir():
            print("Note: The xavani-agent codebase was not included in the backup.")
            print("  If this is a fresh install, run: xavani update")

        if restored_profiles:
            gw_profiles = [n for n, _ in restored_profiles]
            print("\nTo re-enable gateway services for profiles:")
            for pname in gw_profiles:
                print(f"  xavani -p {pname} gateway install")

        print("Done. Your Xavani configuration has been restored.")


# ---------------------------------------------------------------------------
# Quick state snapshots (used by /snapshot slash command and xavani backup --quick)
# ---------------------------------------------------------------------------

# Critical state files to include in quick snapshots (relative to XAVANI_HOME).
# Everything else is either regeneratable (logs, cache) or managed separately
# (skills, repo, sessions/).
#
# Entries may be individual files OR directories.  Directories are captured
# recursively; missing entries are silently skipped.  Pairing data lives in
# platform-specific JSON blobs outside state.db, so it's listed here explicitly
# — `xavani update` snapshots this set before pulling so approved-user lists
# are recoverable if anything goes wrong (issue #15733).
_QUICK_STATE_FILES = (
    "state.db",
    "config.yaml",
    ".env",
    "auth.json",
    "cron/jobs.json",
    "gateway_state.json",
    "channel_directory.json",
    "processes.json",
    # Pairing stores (generic + per-platform JSONs outside state.db)
    "pairing",                          # legacy location (gateway/pairing.py)
    "platforms/pairing",                # new location (gateway/pairing.py)
    "feishu_comment_pairing.json",      # Feishu comment subscription pairings
)

_QUICK_SNAPSHOTS_DIR = "state-snapshots"
_QUICK_DEFAULT_KEEP = 20


def _quick_snapshot_root(xavani_home: Optional[Path] = None) -> Path:
    home = xavani_home or get_xavani_home()
    return home / _QUICK_SNAPSHOTS_DIR


def create_quick_snapshot(
    label: Optional[str] = None,
    xavani_home: Optional[Path] = None,
) -> Optional[str]:
    """Create a quick state snapshot of critical files.

    Copies STATE_FILES to a timestamped directory under state-snapshots/.
    Auto-prunes old snapshots beyond the keep limit.

    Returns:
        Snapshot ID (timestamp-based), or None if no files found.
    """
    home = xavani_home or get_xavani_home()
    root = _quick_snapshot_root(home)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    snap_id = f"{ts}-{label}" if label else ts
    snap_dir = root / snap_id
    snap_dir.mkdir(parents=True, exist_ok=True)

    manifest: Dict[str, int] = {}  # rel_path -> file size

    for rel in _QUICK_STATE_FILES:
        src = home / rel
        if not src.exists():
            continue

        if src.is_dir():
            # Walk the directory and record each file individually in the
            # manifest so restore can treat them uniformly.  Empty dirs are
            # skipped (nothing to snapshot).
            for sub in src.rglob("*"):
                if not sub.is_file():
                    continue
                sub_rel = sub.relative_to(home).as_posix()
                dst = snap_dir / sub_rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(sub, dst)
                    manifest[sub_rel] = dst.stat().st_size
                except (OSError, PermissionError) as exc:
                    logger.warning("Could not snapshot %s: %s", sub_rel, exc)
            continue

        if not src.is_file():
            continue

        dst = snap_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)

        try:
            if src.suffix == ".db":
                if not _safe_copy_db(src, dst):
                    continue
            else:
                shutil.copy2(src, dst)
            manifest[rel] = dst.stat().st_size
        except (OSError, PermissionError) as exc:
            logger.warning("Could not snapshot %s: %s", rel, exc)

    if not manifest:
        shutil.rmtree(snap_dir, ignore_errors=True)
        return None

    # Write manifest
    meta = {
        "id": snap_id,
        "timestamp": ts,
        "label": label,
        "file_count": len(manifest),
        "total_size": sum(manifest.values()),
        "files": manifest,
    }
    with open(snap_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    # Auto-prune
    _prune_quick_snapshots(root, keep=_QUICK_DEFAULT_KEEP)

    logger.info("State snapshot created: %s (%d files)", snap_id, len(manifest))
    return snap_id


def list_quick_snapshots(
    limit: int = 20,
    xavani_home: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """List existing quick state snapshots, most recent first."""
    root = _quick_snapshot_root(xavani_home)
    if not root.exists():
        return []

    results = []
    for d in sorted(root.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        manifest_path = d / "manifest.json"
        if manifest_path.exists():
            try:
                with open(manifest_path, encoding="utf-8") as f:
                    results.append(json.load(f))
            except (json.JSONDecodeError, OSError):
                results.append({"id": d.name, "file_count": 0, "total_size": 0})
        if len(results) >= limit:
            break

    return results


def restore_quick_snapshot(
    snapshot_id: str,
    xavani_home: Optional[Path] = None,
) -> bool:
    """Restore state from a quick snapshot.

    Overwrites current state files with the snapshot's copies.
    Returns True if at least one file was restored.
    """
    home = xavani_home or get_xavani_home()
    root = _quick_snapshot_root(home)
    snap_dir = root / snapshot_id

    if not snap_dir.is_dir():
        return False

    manifest_path = snap_dir / "manifest.json"
    if not manifest_path.exists():
        return False

    with open(manifest_path, encoding="utf-8") as f:
        meta = json.load(f)

    restored = 0
    for rel in meta.get("files", {}):
        src = snap_dir / rel
        if not src.exists():
            continue

        dst = home / rel
        dst.parent.mkdir(parents=True, exist_ok=True)

        try:
            if dst.suffix == ".db":
                # Atomic-ish replace for databases
                tmp = dst.parent / f".{dst.name}.snap_restore"
                shutil.copy2(src, tmp)
                dst.unlink(missing_ok=True)
                shutil.move(str(tmp), str(dst))
            else:
                shutil.copy2(src, dst)
            restored += 1
        except (OSError, PermissionError) as exc:
            logger.error("Failed to restore %s: %s", rel, exc)

    logger.info("Restored %d files from snapshot %s", restored, snapshot_id)
    return restored > 0


def _prune_quick_snapshots(root: Path, keep: int = _QUICK_DEFAULT_KEEP) -> int:
    """Remove oldest quick snapshots beyond the keep limit. Returns count deleted."""
    if not root.exists():
        return 0

    dirs = sorted(
        (d for d in root.iterdir() if d.is_dir()),
        key=lambda d: d.name,
        reverse=True,
    )

    deleted = 0
    for d in dirs[keep:]:
        try:
            shutil.rmtree(d)
            deleted += 1
        except OSError as exc:
            logger.warning("Failed to prune snapshot %s: %s", d.name, exc)

    return deleted


def prune_quick_snapshots(
    keep: int = _QUICK_DEFAULT_KEEP,
    xavani_home: Optional[Path] = None,
) -> int:
    """Manually prune quick snapshots. Returns count deleted."""
    return _prune_quick_snapshots(_quick_snapshot_root(xavani_home), keep=keep)


def run_quick_backup(args) -> None:
    """CLI entry point for xavani backup --quick."""
    label = getattr(args, "label", None)
    snap_id = create_quick_snapshot(label=label)
    if snap_id:
        print(f"State snapshot created: {snap_id}")
        snaps = list_quick_snapshots()
        print(f"  {len(snaps)} snapshot(s) stored in {display_xavani_home()}/state-snapshots/")
        print(f"  Restore with: /snapshot restore {snap_id}")
    else:
        print("No state files found to snapshot.")


# ---------------------------------------------------------------------------
# Shared full-zip backup helper
# ---------------------------------------------------------------------------

def _write_full_zip_backup(out_path: Path, xavani_root: Path) -> Optional[Path]:
    """Write a full zip snapshot of ``xavani_root`` to ``out_path``.

    Uses the same exclusion rules and SQLite safe-copy as :func:`run_backup`.
    Returns the output path on success, None on failure (nothing to back up,
    or write error — caller should surface the outcome but not raise).
    """
    files_to_add: list[tuple[Path, Path]] = []
    try:
        for dirpath, dirnames, filenames in os.walk(xavani_root, followlinks=False):
            dp = Path(dirpath)
            # Prune excluded directories in-place so os.walk doesn't descend
            dirnames[:] = [d for d in dirnames if d not in _EXCLUDED_DIRS]

            for fname in filenames:
                fpath = dp / fname
                try:
                    rel = fpath.relative_to(xavani_root)
                except ValueError:
                    continue

                if _should_exclude(rel):
                    continue

                # Skip the output zip itself if it already exists inside root.
                try:
                    if fpath.resolve() == out_path.resolve():
                        continue
                except (OSError, ValueError):
                    pass

                files_to_add.append((fpath, rel))
    except OSError as exc:
        logger.warning("Full-zip backup: walk failed: %s", exc)
        return None

    if not files_to_add:
        return None

    try:
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for abs_path, rel_path in files_to_add:
                try:
                    if abs_path.suffix == ".db":
                        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
                            tmp_db = Path(tmp.name)
                        try:
                            if _safe_copy_db(abs_path, tmp_db):
                                zf.write(tmp_db, arcname=str(rel_path))
                        finally:
                            tmp_db.unlink(missing_ok=True)
                    else:
                        zf.write(abs_path, arcname=str(rel_path))
                except (PermissionError, OSError, ValueError) as exc:
                    logger.debug("Skipping %s in zip backup: %s", rel_path, exc)
                    continue
    except OSError as exc:
        logger.warning("Full-zip backup: zip write failed: %s", exc)
        # Best-effort cleanup of partial file
        try:
            out_path.unlink(missing_ok=True)
        except OSError:
            pass
        return None

    return out_path


# ---------------------------------------------------------------------------
# Pre-update auto-backup
# ---------------------------------------------------------------------------

_PRE_UPDATE_BACKUPS_DIR = "backups"
_PRE_UPDATE_PREFIX = "pre-update-"
_PRE_UPDATE_DEFAULT_KEEP = 5


def _pre_update_backup_dir(xavani_home: Optional[Path] = None) -> Path:
    home = xavani_home or get_xavani_home()
    return home / _PRE_UPDATE_BACKUPS_DIR


def _prune_pre_update_backups(backup_dir: Path, keep: int) -> int:
    """Remove oldest pre-update backups beyond the keep limit.

    Returns the number of files deleted.  Only touches files matching
    ``pre-update-*.zip`` so hand-made zips dropped in the same directory
    are never touched.

    ``keep`` is floored to 1 because this helper is only called immediately
    after a fresh backup is written: deleting that backup right after the
    user paid the disk/CPU cost to create it would leave them worse off
    than no backup at all (and the wrapper in ``main.py`` would still print
    a misleading ``Saved: <path>`` line for a file that no longer exists).
    Operators who genuinely don't want a backup should set
    ``updates.pre_update_backup: false`` in config — that gates creation.
    """
    keep = max(keep, 1)
    if not backup_dir.exists():
        return 0

    backups = sorted(
        (p for p in backup_dir.iterdir()
         if p.is_file() and p.name.startswith(_PRE_UPDATE_PREFIX) and p.suffix.lower() == ".zip"),
        key=lambda p: p.name,
        reverse=True,
    )

    deleted = 0
    for p in backups[keep:]:
        try:
            p.unlink()
            deleted += 1
        except OSError as exc:
            logger.warning("Failed to prune backup %s: %s", p.name, exc)

    return deleted


def create_pre_update_backup(
    xavani_home: Optional[Path] = None,
    keep: int = _PRE_UPDATE_DEFAULT_KEEP,
) -> Optional[Path]:
    """Create a full zip backup of XAVANI_HOME under ``backups/``.

    Mirrors :func:`run_backup` (same exclusion rules, same SQLite safe-copy)
    but writes to ``<XAVANI_HOME>/backups/pre-update-<timestamp>.zip`` and
    auto-prunes old pre-update backups.

    Returns the path to the created zip, or ``None`` if no files were
    found or the backup could not be created.  Never raises — the caller
    (``xavani update``) should continue even if the backup fails.
    """
    xavani_root = xavani_home or get_default_xavani_root()
    if not xavani_root.is_dir():
        return None

    backup_dir = _pre_update_backup_dir(xavani_root)
    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.warning("Could not create pre-update backup dir %s: %s", backup_dir, exc)
        return None

    stamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    out_path = backup_dir / f"{_PRE_UPDATE_PREFIX}{stamp}.zip"

    result = _write_full_zip_backup(out_path, xavani_root)
    if result is None:
        return None

    _prune_pre_update_backups(backup_dir, keep=keep)
    return out_path


# ---------------------------------------------------------------------------
# Pre-migration auto-backup (used by `xavani claw migrate`)
# ---------------------------------------------------------------------------

_PRE_MIGRATION_PREFIX = "pre-migration-"
_PRE_MIGRATION_DEFAULT_KEEP = 5


def _prune_pre_migration_backups(backup_dir: Path, keep: int) -> int:
    """Remove oldest pre-migration backups beyond the keep limit.

    Only touches files matching ``pre-migration-*.zip`` so other backups in
    the same directory are never touched.
    """
    keep = max(keep, 0)
    if not backup_dir.exists():
        return 0

    backups = sorted(
        (p for p in backup_dir.iterdir()
         if p.is_file() and p.name.startswith(_PRE_MIGRATION_PREFIX) and p.suffix.lower() == ".zip"),
        key=lambda p: p.name,
        reverse=True,
    )

    deleted = 0
    for p in backups[keep:]:
        try:
            p.unlink()
            deleted += 1
        except OSError as exc:
            logger.warning("Failed to prune pre-migration backup %s: %s", p.name, exc)

    return deleted


def create_pre_migration_backup(
    xavani_home: Optional[Path] = None,
    keep: int = _PRE_MIGRATION_DEFAULT_KEEP,
) -> Optional[Path]:
    """Create a full zip backup of XAVANI_HOME under ``backups/`` before a
    ``xavani claw migrate`` apply.

    Shares implementation with :func:`create_pre_update_backup` via
    ``_write_full_zip_backup`` — same exclusions, same SQLite safe-copy,
    restorable with ``xavani import <archive>``.  Writes to
    ``<XAVANI_HOME>/backups/pre-migration-<timestamp>.zip`` and auto-prunes
    old pre-migration backups.

    Returns the path to the created zip, or ``None`` if nothing was found
    to back up (fresh install) or the write failed.  Never raises — the
    caller decides whether to abort or proceed.
    """
    xavani_root = xavani_home or get_default_xavani_root()
    if not xavani_root.is_dir():
        return None

    # Reuses the shared backups/ directory so `xavani import` and the
    # update-backup listing pick up pre-migration archives too.
    backup_dir = _pre_update_backup_dir(xavani_root)
    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.warning("Could not create pre-migration backup dir %s: %s", backup_dir, exc)
        return None

    stamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    out_path = backup_dir / f"{_PRE_MIGRATION_PREFIX}{stamp}.zip"

    result = _write_full_zip_backup(out_path, xavani_root)
    if result is None:
        return None

    _prune_pre_migration_backups(backup_dir, keep=keep)
    return out_path


_SQLITE_HEADER = b"SQLite format 3\0"

DEFAULT_INTEGRITY_CHECK_MAX_BYTES = 2 << 30


def verify_sqlite_integrity(
    path: Path,
    *,
    check_header: bool = True,
    run_pragma: bool = True,
    max_bytes: int = DEFAULT_INTEGRITY_CHECK_MAX_BYTES,
) -> dict:
    result: dict = {"valid": False, "message": "", "size": None}

    try:
        st = path.stat()
    except FileNotFoundError:
        result["message"] = f"not found: {path}"
        return result
    except OSError as exc:
        result["message"] = f"cannot stat: {exc}"
        return result

    result["size"] = st.st_size

    if st.st_size < 100:
        result["message"] = f"too small ({st.st_size} bytes) to be a valid SQLite database"
        return result

    oversized = max_bytes > 0 and st.st_size > max_bytes

    if check_header:
        from xavani_cli.sqlite_safe_read import read_header_bytes_preopen

        head = read_header_bytes_preopen(path, length=len(_SQLITE_HEADER))
        if head is None:
            result["valid"] = False
            result["message"] = "cannot read header"
            return result
        if head != _SQLITE_HEADER:
            result["valid"] = False
            result["message"] = (
                f"missing SQLite header magic (got {head[:16].hex()!r})"
            )
            return result

    if oversized:
        run_pragma = False
        probe = None
        try:
            probe = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=1.0)
            probe.execute("PRAGMA schema_version").fetchone()
            probe.execute("SELECT count(*) FROM sqlite_master").fetchone()
            result["valid"] = True
            result["message"] = (
                f"size {st.st_size:,} bytes exceeds max_bytes {max_bytes:,}; "
                "skipped PRAGMA integrity_check (header + schema probe passed)"
            )
        except sqlite3.DatabaseError as exc:
            result["valid"] = False
            result["message"] = f"schema probe failed: {exc}"
            return result
        except Exception as exc:
            result["valid"] = False
            result["message"] = f"schema probe error: {exc}"
            return result
        finally:
            if probe is not None:
                try:
                    probe.close()
                except Exception:
                    pass

    if run_pragma:
        conn = None
        try:
            conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=1.0)
            cursor = conn.execute("PRAGMA integrity_check")
            rows = cursor.fetchall()
            if len(rows) == 1 and rows[0][0] == "ok":
                result["valid"] = True
                result["message"] = "integrity check passed"
                return result
            errors = [str(r[0]) for r in rows]
            result["message"] = f"integrity check failed: {'; '.join(errors[:5])}"
            return result
        except sqlite3.DatabaseError as exc:
            result["message"] = f"cannot open database: {exc}"
            return result
        except Exception as exc:
            result["message"] = f"integrity check error: {exc}"
            return result
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

    result["valid"] = True
    if not result["message"]:
        result["message"] = "header check passed"
    return result


def copy_db_and_verify(src: Path, dst: Path) -> bool:
    if not _safe_copy_db(src, dst):
        return False
    integrity = verify_sqlite_integrity(dst, run_pragma=True)
    if not integrity.get("valid"):
        try:
            dst.unlink(missing_ok=True)
        except OSError:
            pass
        logger.warning("Backup of %s failed integrity verification: %s", src, integrity.get("message"))
        return False
    return True


def _foreign_db_holder_pids(db_path: Path) -> Optional[List[int]]:
    if not sys.platform.startswith("linux"):
        return None

    def _canonical(path: str) -> str:
        return os.path.normcase(
            os.path.abspath(path.removesuffix(" (deleted)"))
        )

    canonical_db = _canonical(os.fspath(db_path))
    watched = {canonical_db, canonical_db + "-wal", canonical_db + "-shm"}
    pids: List[int] = []
    try:
        own_pid = os.getpid()
        for pid_str in os.listdir("/proc"):
            if not pid_str.isdigit():
                continue
            pid = int(pid_str)
            if pid == own_pid:
                continue
            fd_dir = f"/proc/{pid}/fd"
            try:
                fds = os.listdir(fd_dir)
            except OSError:
                continue
            for fd in fds:
                try:
                    target = os.readlink(f"{fd_dir}/{fd}")
                except OSError:
                    continue
                if _canonical(target) in watched:
                    pids.append(pid)
                    break
    except OSError:
        return None
    return pids


def _safe_restore_db(src: Path, dst: Path) -> bool:
    try:
        dst_conn = sqlite3.connect(str(dst))
        try:
            dst_conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except Exception:
            pass
        src_conn = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
        try:
            src_conn.backup(dst_conn)
        finally:
            src_conn.close()
        dst_conn.close()
        try:
            mode = src.stat().st_mode
            dst.chmod(mode)
        except Exception:
            pass
        return True
    except Exception as exc:
        logger.warning("SQLite safe restore failed for %s -> %s: %s", src, dst, exc)
        from xavani_cli.sqlite_safe_read import (
            LiveConnectionError,
            offline_file_access,
        )

        try:
            holders = _foreign_db_holder_pids(dst)
            if holders:
                logger.error(
                    "Refusing unlink+move restore of %s: process(es) %s still "
                    "hold the database or its WAL open. Stop them and retry.",
                    dst, holders,
                )
                return False
            with offline_file_access(dst, what="unlink+move restore of"):
                tmp = dst.parent / f".{dst.name}.snap_restore"
                shutil.copy2(src, tmp)
                dst.unlink(missing_ok=True)
                for _sidecar_suffix in ("-wal", "-shm", "-journal"):
                    dst.with_name(dst.name + _sidecar_suffix).unlink(missing_ok=True)
                shutil.move(str(tmp), str(dst))
            return True
        except LiveConnectionError as exc2:
            logger.error(
                "Refusing unlink+move restore of %s: %s Close the in-process "
                "database handles (or restart Xavani) and retry.",
                dst, exc2,
            )
            return False
        except Exception as exc2:
            logger.error("Fallback restore also failed for %s -> %s: %s", src, dst, exc2)
            return False


_CRON_JOBS_REL = "cron/jobs.json"


def _count_cron_jobs(path: Path) -> Optional[int]:
    if not path.is_file():
        return None
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(data, dict):
        jobs = data.get("jobs", [])
        return len(jobs) if isinstance(jobs, list) else None
    if isinstance(data, list):
        return len(data)
    return None


def restore_cron_jobs_if_emptied(
    snapshot_id: str,
    xavani_home: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    if not snapshot_id:
        return None

    home = xavani_home or get_xavani_home()
    live_path = home / _CRON_JOBS_REL

    live_count = _count_cron_jobs(live_path)
    if live_count is None:
        return None

    snap_path = _quick_snapshot_root(home) / snapshot_id / _CRON_JOBS_REL
    snap_count = _count_cron_jobs(snap_path)
    if not snap_count:
        return None

    if live_count >= snap_count:
        return None

    try:
        live_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(snap_path, live_path)
    except (OSError, PermissionError) as exc:
        logger.error(
            "Cron jobs were emptied during update but auto-restore failed: %s", exc
        )
        return None

    logger.warning(
        "Restored %d cron job(s) from pre-update snapshot %s "
        "(live file had %d job(s), snapshot had %d — jobs were lost during migration)",
        snap_count,
        snapshot_id,
        live_count,
        snap_count,
    )
    return {"restored": True, "job_count": snap_count, "snapshot_id": snapshot_id}


def _sibling_profile_homes(invoking_home: Path) -> list[tuple[str, Path]]:
    homes: list[tuple[str, Path]] = []
    try:
        from xavani_cli.profiles import (
            _get_default_xavani_home,
            _get_profiles_root,
            _PROFILE_ID_RE,
        )

        invoking = invoking_home.resolve()
        default_home = _get_default_xavani_home()
        if default_home.is_dir() and default_home.resolve() != invoking:
            homes.append(("default", default_home))
        root = _get_profiles_root()
        if root.is_dir():
            for entry in sorted(root.iterdir()):
                if (
                    entry.is_dir()
                    and entry.name != "default"
                    and _PROFILE_ID_RE.match(entry.name)
                    and entry.resolve() != invoking
                ):
                    homes.append((entry.name, entry))
    except Exception as exc:
        logger.debug("Sibling profile enumeration failed: %s", exc)
    return homes


def create_pre_update_snapshots_all_profiles(
    invoking_home: Optional[Path] = None,
    keep: Optional[int] = None,
    max_file_size: Optional[int] = None,
) -> Dict[str, str]:
    results: Dict[str, str] = {}
    home = invoking_home or get_xavani_home()
    for name, profile_home in _sibling_profile_homes(home):
        try:
            snap_id = create_quick_snapshot(
                label="pre-update",
                xavani_home=profile_home,
            )
            if snap_id:
                results[name] = snap_id
        except Exception as exc:
            logger.debug("Pre-update snapshot for profile %s failed: %s", name, exc)
    return results


_PROTECTED_CONFIG_PATHS: Tuple[Tuple[str, ...], ...] = (
    ("model", "provider"),
    ("model", "default"),
    ("model", "base_url"),
    ("model", "api_key"),
    ("moa",),
)


def _read_raw_yaml_dict(path: Path) -> Optional[Dict[str, Any]]:
    if not path.is_file():
        return None
    try:
        import yaml

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _get_config_path_value(data: Dict[str, Any], dotted: Tuple[str, ...]) -> Any:
    node: Any = data
    for key in dotted:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def _set_config_path_value(data: Dict[str, Any], dotted: Tuple[str, ...], value: Any) -> None:
    node = data
    for key in dotted[:-1]:
        child = node.get(key)
        if not isinstance(child, dict):
            child = {}
            node[key] = child
        node = child
    node[dotted[-1]] = value


def restore_config_model_settings_if_rewritten(
    snapshot_id: str,
    xavani_home: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    if not snapshot_id:
        return None

    home = xavani_home or get_xavani_home()
    live_path = home / "config.yaml"
    snap_path = _quick_snapshot_root(home) / snapshot_id / "config.yaml"

    snap = _read_raw_yaml_dict(snap_path)
    if not snap:
        return None
    live = _read_raw_yaml_dict(live_path)
    if live is None:
        return None

    restored_keys: list[str] = []
    for dotted in _PROTECTED_CONFIG_PATHS:
        snap_val = _get_config_path_value(snap, dotted)
        if snap_val in (None, "", {}, []):
            continue
        live_val = _get_config_path_value(live, dotted)
        if live_val == snap_val:
            continue
        _set_config_path_value(live, dotted, snap_val)
        restored_keys.append(".".join(dotted))

    if not restored_keys:
        return None

    try:
        from utils import atomic_yaml_write

        atomic_yaml_write(live_path, live)
    except (OSError, PermissionError) as exc:
        logger.error(
            "config.yaml model settings were rewritten during update but "
            "auto-restore failed: %s",
            exc,
        )
        return None

    logger.warning(
        "Restored user config value(s) %s from pre-update snapshot %s — "
        "the update flow rewrote them (#64160)",
        ", ".join(restored_keys),
        snapshot_id,
    )
    return {"restored": True, "keys": restored_keys, "snapshot_id": snapshot_id}


def restore_config_model_settings_all_profiles(
    profile_snapshots: Dict[str, str],
    invoking_home: Optional[Path] = None,
) -> list[Dict[str, Any]]:
    restored: list[Dict[str, Any]] = []
    if not profile_snapshots:
        return restored
    home = invoking_home or get_xavani_home()
    by_name = dict(_sibling_profile_homes(home))
    for name, snap_id in profile_snapshots.items():
        profile_home = by_name.get(name)
        if profile_home is None:
            continue
        try:
            result = restore_config_model_settings_if_rewritten(
                snap_id, xavani_home=profile_home
            )
        except Exception as exc:
            logger.debug(
                "Config model-settings restore check for profile %s failed: %s",
                name,
                exc,
            )
            continue
        if result:
            result["profile"] = name
            restored.append(result)
    return restored


def restore_cron_jobs_all_profiles(
    profile_snapshots: Dict[str, str],
    invoking_home: Optional[Path] = None,
) -> list[Dict[str, Any]]:
    restored: list[Dict[str, Any]] = []
    if not profile_snapshots:
        return restored
    home = invoking_home or get_xavani_home()
    by_name = dict(_sibling_profile_homes(home))
    for name, snap_id in profile_snapshots.items():
        profile_home = by_name.get(name)
        if profile_home is None:
            continue
        try:
            result = restore_cron_jobs_if_emptied(snap_id, xavani_home=profile_home)
        except Exception as exc:
            logger.debug("Cron restore check for profile %s failed: %s", name, exc)
            continue
        if result:
            result["profile"] = name
            restored.append(result)
    return restored
