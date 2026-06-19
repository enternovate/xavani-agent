#!/usr/bin/env python3

# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Automatic file organizer — tidy the user's folders, safely and reversibly.

This module gives the agent a capability to keep folders like Downloads,
Desktop, Documents and screenshots organized into category subfolders
(Images/, PDFs/, Archives/, ...).  It can run three ways:

  * **preview**  — show what *would* move, touching nothing (the default).
  * **organize** — perform the moves once, recording an undo manifest.
  * **watch**    — a lightweight background poller that organizes new files
                   as they land ("real-time", cross-platform, stdlib-only).

Design is safety-first because it moves the user's real files:

  * never deletes anything — only moves,
  * never overwrites — collisions get a " (1)", " (2)" suffix,
  * skips files still being written (partial downloads, very recent mtime),
  * skips hidden/system files and the category folders themselves,
  * idempotent — running twice does nothing the second time,
  * fully reversible — every move is logged so ``undo`` can put it back.

The agent reaches this through the ``organize_files`` tool (registered at the
bottom).  Humans can drive the same engine from the CLI::

    python -m tools.file_organizer preview ~/Downloads
    python -m tools.file_organizer organize ~/Downloads --yes
    python -m tools.file_organizer watch            # foreground daemon
    python -m tools.file_organizer install-autostart  # run at login
    python -m tools.file_organizer undo
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

logger = logging.getLogger(__name__)
try:
    from xavani_cli.safe_logging import SafeLogFilter
    SafeLogFilter.install()
except Exception:
    pass


# ---------------------------------------------------------------------------
# Classification rules
# ---------------------------------------------------------------------------
# Extension -> category.  Extensions are stored WITHOUT a leading dot and are
# matched case-insensitively.  "Screenshots" carries no extensions because it
# is matched by filename pattern (below), not by suffix.  Anything unmatched
# falls into "Other".  Override or extend via config.yaml -> file_organizer.
CATEGORY_RULES: dict[str, set[str]] = {
    "Screenshots": set(),
    "Images": {
        "jpg", "jpeg", "png", "gif", "bmp", "svg", "webp", "heic", "heif",
        "tiff", "tif", "ico", "raw", "cr2", "nef", "avif",
    },
    "PDFs": {"pdf"},
    "Documents": {
        "doc", "docx", "odt", "rtf", "txt", "md", "markdown", "pages",
        "tex", "epub", "mobi",
    },
    "Spreadsheets": {"xls", "xlsx", "ods", "csv", "tsv", "numbers"},
    "Presentations": {"ppt", "pptx", "odp", "key"},
    "Archives": {"zip", "tar", "gz", "tgz", "bz2", "xz", "rar", "7z", "z"},
    "Audio": {"mp3", "wav", "flac", "aac", "ogg", "m4a", "wma", "aiff"},
    "Video": {"mp4", "mov", "avi", "mkv", "webm", "wmv", "flv", "m4v", "mpg", "mpeg"},
    "Code": {
        "py", "js", "ts", "tsx", "jsx", "java", "c", "cpp", "cc", "h", "hpp",
        "go", "rs", "rb", "php", "swift", "kt", "sh", "bash", "html", "css", "scss",
    },
    "Data": {"json", "xml", "yaml", "yml", "toml", "sql", "db", "sqlite", "parquet", "ndjson"},
    "Installers": {"dmg", "pkg", "exe", "msi", "deb", "rpm", "appimage", "apk"},
}

# A file whose name contains one of these (and looks like an image/video) is a
# screenshot regardless of extension — keep them out of the generic Images pile.
_SCREENSHOT_HINTS = (
    "screenshot", "screen shot", "screen recording", "captura de pantalla",
)

# Files we never touch.
_SYSTEM_FILES = {".ds_store", "thumbs.db", "desktop.ini", ".localized"}
_PARTIAL_SUFFIXES = {
    ".crdownload", ".part", ".partial", ".download", ".tmp",
    ".opdownload", ".!ut", ".aria2",
}

# Default: leave a file alone until it has been untouched for this long, so we
# never grab something mid-download / mid-save.
DEFAULT_MIN_AGE_SECONDS = 10.0
DEFAULT_WATCH_INTERVAL_SECONDS = 5.0


def _ext(name: str) -> str:
    """Return the lowercase extension (no dot) of *name*, '' if none."""
    return Path(name).suffix.lower().lstrip(".")


def categorize(name: str) -> str:
    """Classify a filename into a category folder name.

    Total function: always returns a key of :data:`CATEGORY_RULES` or
    ``"Other"`` — never raises, never returns ``None``.
    """
    low = name.lower()
    ext = _ext(name)
    if any(hint in low for hint in _SCREENSHOT_HINTS):
        if not ext or ext in CATEGORY_RULES["Images"] or ext in CATEGORY_RULES["Video"]:
            return "Screenshots"
    for category, extensions in CATEGORY_RULES.items():
        if ext and ext in extensions:
            return category
    return "Other"


# ---------------------------------------------------------------------------
# Plan / result data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Move:
    """A single planned move: ``src`` -> ``dst`` under category folder."""
    src: Path
    dst: Path
    category: str


@dataclass
class OrganizeResult:
    moved: list[tuple[Path, Path]] = field(default_factory=list)
    skipped: list[tuple[Path, str]] = field(default_factory=list)
    errors: list[tuple[Path, str]] = field(default_factory=list)
    dry_run: bool = False
    manifest_path: Optional[Path] = None

    def summary(self) -> str:
        verb = "Would move" if self.dry_run else "Moved"
        by_cat: dict[str, int] = {}
        for _src, dst in self.moved:
            by_cat[dst.parent.name] = by_cat.get(dst.parent.name, 0) + 1
        parts = ", ".join(f"{n} → {cat}/" for cat, n in sorted(by_cat.items()))
        line = f"{verb} {len(self.moved)} file(s)"
        if parts:
            line += f" ({parts})"
        if self.skipped:
            line += f"; skipped {len(self.skipped)}"
        if self.errors:
            line += f"; {len(self.errors)} error(s)"
        return line


@dataclass
class UndoResult:
    restored: list[tuple[Path, Path]] = field(default_factory=list)
    errors: list[tuple[Path, str]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------

def _skip_reason(entry: Path, now: float, min_age_seconds: float) -> Optional[str]:
    """Return why *entry* should be skipped, or ``None`` to organize it."""
    name = entry.name
    if name.startswith("."):
        return "hidden"
    if name.startswith("~$"):
        return "office-temp"
    if name.lower() in _SYSTEM_FILES:
        return "system"
    if entry.suffix.lower() in _PARTIAL_SUFFIXES:
        return "partial-download"
    try:
        mtime = entry.stat().st_mtime
    except OSError:
        return "stat-failed"
    if now - mtime < min_age_seconds:
        return "recently-modified"
    return None


def _scan(folder: Path, now: float, min_age_seconds: float
          ) -> tuple[list[Move], list[tuple[Path, str]]]:
    """Scan the *top level* of *folder*, returning (moves, skips).

    Subdirectories — which include the category folders we create — are never
    descended into and never moved, which is what makes the operation
    idempotent and safe to repeat.
    """
    moves: list[Move] = []
    skips: list[tuple[Path, str]] = []
    try:
        entries = sorted(folder.iterdir(), key=lambda p: p.name.lower())
    except OSError as exc:
        logger.warning("file_organizer: cannot list %s: %s", folder, exc)
        return moves, skips

    for entry in entries:
        # Leave every directory (incl. our category folders) and symlinks alone.
        if entry.is_symlink() or entry.is_dir():
            continue
        reason = _skip_reason(entry, now, min_age_seconds)
        if reason:
            skips.append((entry, reason))
            continue
        category = categorize(entry.name)
        moves.append(Move(entry, folder / category / entry.name, category))
    return moves, skips


def plan_organization(folder, *, min_age_seconds: float = DEFAULT_MIN_AGE_SECONDS,
                      now: Optional[float] = None) -> list[Move]:
    """Return the list of moves that organizing *folder* would perform."""
    folder = Path(folder).expanduser()
    if not folder.is_dir():
        return []
    now = time.time() if now is None else now
    moves, _ = _scan(folder, now, min_age_seconds)
    return moves


def _dedupe_path(dst: Path) -> Path:
    """Return *dst*, or the first ``stem (N).suffix`` variant that is free."""
    if not dst.exists():
        return dst
    stem, suffix, parent = dst.stem, dst.suffix, dst.parent
    n = 1
    while True:
        candidate = parent / f"{stem} ({n}){suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def safe_move(src: Path, dst: Path) -> Path:
    """Move *src* to *dst*, creating parents and never overwriting.

    Returns the path the file actually landed at (which differs from *dst*
    when a same-named file was already there).
    """
    src, dst = Path(src), Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    final = _dedupe_path(dst)
    shutil.move(str(src), str(final))
    return final


def _append_manifest(manifest_path: Path, src: Path, dst: Path, category: str) -> None:
    manifest_path = Path(manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "src": str(src), "dst": str(dst),
        "category": category, "ts": time.time(),
    }
    with manifest_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


def organize_folder(folder, *, dry_run: bool = False,
                    min_age_seconds: float = DEFAULT_MIN_AGE_SECONDS,
                    manifest_path=None) -> OrganizeResult:
    """Organize a single folder. Records an undo manifest when *manifest_path*
    is given and not a dry run."""
    folder = Path(folder).expanduser()
    result = OrganizeResult(dry_run=dry_run,
                            manifest_path=Path(manifest_path) if manifest_path else None)
    if not folder.is_dir():
        result.errors.append((folder, "not a directory"))
        return result

    now = time.time()
    moves, skips = _scan(folder, now, min_age_seconds)
    result.skipped = skips

    for move in moves:
        if dry_run:
            result.moved.append((move.src, move.dst))
            continue
        try:
            final = safe_move(move.src, move.dst)
            result.moved.append((move.src, final))
            if manifest_path:
                _append_manifest(Path(manifest_path), move.src, final, move.category)
        except Exception as exc:  # one bad file must not abort the rest
            logger.warning("file_organizer: failed to move %s: %s", move.src, exc)
            result.errors.append((move.src, str(exc)))
    return result


def organize_folders(folders: Iterable, *, dry_run: bool = False,
                     min_age_seconds: float = DEFAULT_MIN_AGE_SECONDS,
                     manifest_path=None) -> OrganizeResult:
    """Organize several folders, aggregating into one result."""
    agg = OrganizeResult(dry_run=dry_run,
                         manifest_path=Path(manifest_path) if manifest_path else None)
    for folder in folders:
        r = organize_folder(folder, dry_run=dry_run,
                            min_age_seconds=min_age_seconds, manifest_path=manifest_path)
        agg.moved.extend(r.moved)
        agg.skipped.extend(r.skipped)
        agg.errors.extend(r.errors)
    return agg


def undo(manifest_path) -> UndoResult:
    """Reverse the moves recorded in *manifest_path*, newest first."""
    manifest_path = Path(manifest_path)
    result = UndoResult()
    if not manifest_path.exists():
        return result
    try:
        lines = manifest_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        result.errors.append((manifest_path, str(exc)))
        return result

    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            dst, src = Path(rec["dst"]), Path(rec["src"])
        except (json.JSONDecodeError, KeyError) as exc:
            result.errors.append((manifest_path, f"bad manifest line: {exc}"))
            continue
        if not dst.exists():
            result.errors.append((dst, "moved file no longer present"))
            continue
        try:
            final = safe_move(dst, src)
            result.restored.append((dst, final))
        except Exception as exc:
            result.errors.append((dst, str(exc)))

    # Archive the manifest so a second undo doesn't try to run it again.
    try:
        manifest_path.rename(manifest_path.with_name(manifest_path.name + ".done"))
    except OSError:
        pass
    return result


# ---------------------------------------------------------------------------
# Config + default targets
# ---------------------------------------------------------------------------

def _user_config() -> dict:
    """Return the ``file_organizer`` section of config.yaml, or {}."""
    try:
        from xavani_cli.config import load_config
        cfg = load_config() or {}
        sub = cfg.get("file_organizer")
        return sub if isinstance(sub, dict) else {}
    except Exception:
        return {}


def default_target_folders() -> list[Path]:
    """The folders organized by default (user-chosen: Downloads, Desktop,
    Documents, plus Pictures/Screenshots when present)."""
    configured = _user_config().get("folders")
    if configured:
        return [Path(p).expanduser() for p in configured]
    home = Path.home()
    folders = [home / "Downloads", home / "Desktop", home / "Documents"]
    pictures = home / "Pictures"
    if pictures.is_dir():
        folders.append(pictures)
    return folders


def _state_dir() -> Path:
    """Directory for the manifest, watcher pidfile and watcher log."""
    d = Path.home() / ".xavani" / "file_organizer"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _default_manifest_path() -> Path:
    return _state_dir() / "manifest.jsonl"


# ---------------------------------------------------------------------------
# Real-time watcher (stdlib polling — no third-party deps, works on Windows)
# ---------------------------------------------------------------------------

def watch(folders, *, interval: float = DEFAULT_WATCH_INTERVAL_SECONDS,
          min_age_seconds: float = DEFAULT_MIN_AGE_SECONDS,
          manifest_path=None, stop_event=None, log=logger.info) -> None:
    """Poll *folders* and organize new files as they settle.

    Runs until *stop_event* is set (or Ctrl-C). Polling beats filesystem
    events here: it is dependency-free, behaves identically on macOS / Windows
    / Linux, and a few folders every few seconds is negligible cost.
    """
    folders = [Path(f).expanduser() for f in folders]
    manifest_path = Path(manifest_path) if manifest_path else _default_manifest_path()
    log("xavani-organize: watching %s (every %ss)",
        ", ".join(str(f) for f in folders), interval)
    try:
        while stop_event is None or not stop_event.is_set():
            for folder in folders:
                if not folder.is_dir():
                    continue
                res = organize_folder(folder, dry_run=False,
                                      min_age_seconds=min_age_seconds,
                                      manifest_path=manifest_path)
                for src, dst in res.moved:
                    log("  moved %s → %s/", src.name, dst.parent.name)
            if stop_event is not None:
                stop_event.wait(interval)
            else:
                time.sleep(interval)
    except KeyboardInterrupt:
        log("xavani-organize: stopped")


# ---------------------------------------------------------------------------
# Background process control (used by the agent's watch_start / watch_stop)
# ---------------------------------------------------------------------------

def _pidfile() -> Path:
    return _state_dir() / "watch.pid"


def _watch_logfile() -> Path:
    return _state_dir() / "watch.log"


def _read_pid() -> Optional[int]:
    pf = _pidfile()
    if not pf.exists():
        return None
    try:
        return int(pf.read_text().strip())
    except (OSError, ValueError):
        return None


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    # NB: deliberately NOT a signal-0 os.kill liveness probe — on Windows that
    # is interpreted as CTRL_C_EVENT and hard-kills the target's console group
    # (bpo-14484). psutil.pid_exists is the cross-platform check (psutil is a
    # core dependency); see gateway.status._pid_exists for the same rationale.
    import psutil

    return bool(psutil.pid_exists(pid))


def watcher_running() -> Optional[int]:
    """Return the live watcher pid, or ``None`` if not running."""
    pid = _read_pid()
    if pid and _pid_alive(pid):
        return pid
    return None


def start_watch_process(folders=None, interval: float = DEFAULT_WATCH_INTERVAL_SECONDS) -> int:
    """Spawn a detached background watcher and return its pid."""
    import subprocess

    existing = watcher_running()
    if existing:
        return existing

    folders = [str(Path(f).expanduser()) for f in (folders or default_target_folders())]
    repo_root = Path(__file__).resolve().parents[1]
    cmd = [sys.executable, "-m", "tools.file_organizer", "watch",
           "--interval", str(interval), "--folders", *folders]

    log_fh = open(_watch_logfile(), "a", encoding="utf-8")  # noqa: SIM115 (lives with the child)
    creationflags = 0
    start_new_session = False
    if os.name == "nt":
        creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) | \
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        start_new_session = True  # detach from this process's session/TTY

    proc = subprocess.Popen(
        cmd, cwd=str(repo_root), stdout=log_fh, stderr=log_fh, stdin=subprocess.DEVNULL,
        start_new_session=start_new_session, creationflags=creationflags,
    )
    _pidfile().write_text(str(proc.pid))
    return proc.pid


def stop_watch_process() -> bool:
    """Stop the background watcher. Returns True if one was running."""
    import signal

    pid = watcher_running()
    if not pid:
        _pidfile().unlink(missing_ok=True)
        return False
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass
    _pidfile().unlink(missing_ok=True)
    return True


# ---------------------------------------------------------------------------
# Auto-start installation (run the watcher at login — built, not auto-enabled)
# ---------------------------------------------------------------------------

_AUTOSTART_LABEL = "com.xavani.fileorganizer"


def install_autostart(folders=None, interval: float = DEFAULT_WATCH_INTERVAL_SECONDS,
                      load: bool = True) -> str:
    """Install a per-user auto-start entry so the watcher runs at login.

    Returns a human-readable description of what was installed. Platform-aware:
    launchd (macOS), Task Scheduler (Windows), systemd-user (Linux).
    """
    import subprocess

    folders = [str(Path(f).expanduser()) for f in (folders or default_target_folders())]
    repo_root = Path(__file__).resolve().parents[1]
    args = ["watch", "--interval", str(interval), "--folders", *folders]

    if sys.platform == "darwin":
        plist = Path.home() / "Library" / "LaunchAgents" / f"{_AUTOSTART_LABEL}.plist"
        plist.parent.mkdir(parents=True, exist_ok=True)
        prog_args = "".join(
            f"    <string>{a}</string>\n"
            for a in [sys.executable, "-m", "tools.file_organizer", *args]
        )
        plist.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
            '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
            '<plist version="1.0"><dict>\n'
            f'  <key>Label</key><string>{_AUTOSTART_LABEL}</string>\n'
            f'  <key>ProgramArguments</key><array>\n{prog_args}  </array>\n'
            f'  <key>WorkingDirectory</key><string>{repo_root}</string>\n'
            '  <key>RunAtLoad</key><true/>\n'
            '  <key>KeepAlive</key><true/>\n'
            f'  <key>StandardOutPath</key><string>{_watch_logfile()}</string>\n'
            f'  <key>StandardErrorPath</key><string>{_watch_logfile()}</string>\n'
            '</dict></plist>\n'
        )
        if load:
            subprocess.run(["launchctl", "unload", str(plist)],
                           capture_output=True, check=False)
            subprocess.run(["launchctl", "load", str(plist)],
                           capture_output=True, check=False)
        return f"launchd agent installed at {plist}" + (" and loaded" if load else "")

    if os.name == "nt":
        pythonw = str(Path(sys.executable).with_name("pythonw.exe"))
        runner = pythonw if Path(pythonw).exists() else sys.executable
        quoted = " ".join(f'\\"{a}\\"' if " " in a else a
                          for a in ["-m", "tools.file_organizer", *args])
        task_cmd = f'cmd /c cd /d "{repo_root}" && "{runner}" {quoted}'
        if load:
            subprocess.run(
                ["schtasks", "/Create", "/F", "/SC", "ONLOGON",
                 "/TN", _AUTOSTART_LABEL, "/TR", task_cmd],
                capture_output=True, check=False,
            )
        return f"Windows scheduled task '{_AUTOSTART_LABEL}' installed (runs at logon)"

    # Linux / other: systemd user service.
    unit = Path.home() / ".config" / "systemd" / "user" / f"{_AUTOSTART_LABEL}.service"
    unit.parent.mkdir(parents=True, exist_ok=True)
    exec_args = " ".join([sys.executable, "-m", "tools.file_organizer", *args])
    unit.write_text(
        "[Unit]\nDescription=Xavani file organizer\n\n"
        f"[Service]\nType=simple\nWorkingDirectory={repo_root}\n"
        f"ExecStart={exec_args}\nRestart=always\n\n"
        "[Install]\nWantedBy=default.target\n"
    )
    if load:
        subprocess.run(["systemctl", "--user", "daemon-reload"],
                       capture_output=True, check=False)
        subprocess.run(["systemctl", "--user", "enable", "--now",
                        f"{_AUTOSTART_LABEL}.service"], capture_output=True, check=False)
    return f"systemd user service installed at {unit}" + (" and started" if load else "")


def uninstall_autostart() -> str:
    """Remove the auto-start entry installed by :func:`install_autostart`."""
    import subprocess

    if sys.platform == "darwin":
        plist = Path.home() / "Library" / "LaunchAgents" / f"{_AUTOSTART_LABEL}.plist"
        subprocess.run(["launchctl", "unload", str(plist)],
                       capture_output=True, check=False)
        plist.unlink(missing_ok=True)
        return "launchd agent removed"
    if os.name == "nt":
        subprocess.run(["schtasks", "/Delete", "/F", "/TN", _AUTOSTART_LABEL],
                       capture_output=True, check=False)
        return "Windows scheduled task removed"
    unit = Path.home() / ".config" / "systemd" / "user" / f"{_AUTOSTART_LABEL}.service"
    subprocess.run(["systemctl", "--user", "disable", "--now",
                    f"{_AUTOSTART_LABEL}.service"], capture_output=True, check=False)
    unit.unlink(missing_ok=True)
    return "systemd user service removed"


# ---------------------------------------------------------------------------
# Agent tool: organize_files
# ---------------------------------------------------------------------------
from tools.registry import registry, tool_error, tool_result


def _check_file_reqs():
    """Lazy availability check, shared with the core file toolset."""
    try:
        from tools import check_file_requirements
        return check_file_requirements()
    except Exception:
        return True


def _resolve_folders(args) -> list[Path]:
    raw = args.get("folders")
    if raw:
        return [Path(p).expanduser() for p in raw]
    return default_target_folders()


def organize_files_tool(args: dict) -> str:
    """Handler for the ``organize_files`` agent tool."""
    mode = (args.get("mode") or "preview").lower()
    folders = _resolve_folders(args)
    folder_strs = [str(f) for f in folders]

    if mode == "preview":
        res = organize_folders(folders, dry_run=True)
        plan = [{"file": s.name, "from": str(s.parent), "to": d.parent.name}
                for s, d in res.moved]
        return tool_result(
            mode="preview", folders=folder_strs,
            would_move=len(res.moved), skipped=len(res.skipped),
            plan=plan[:200], summary=res.summary(),
            note="Nothing was moved. Call mode='organize' to apply, or "
                 "mode='watch_start' to keep folders tidy automatically.",
        )

    if mode == "organize":
        manifest = _default_manifest_path()
        res = organize_folders(folders, dry_run=False, manifest_path=manifest)
        return tool_result(
            mode="organize", folders=folder_strs,
            moved=len(res.moved), skipped=len(res.skipped), errors=len(res.errors),
            summary=res.summary(), manifest=str(manifest),
            undo="Call mode='undo' to reverse this.",
        )

    if mode == "watch_start":
        interval = float(args.get("interval") or DEFAULT_WATCH_INTERVAL_SECONDS)
        pid = start_watch_process(folders=folder_strs, interval=interval)
        return tool_result(
            mode="watch_start", running=True, pid=pid, folders=folder_strs,
            interval=interval, log=str(_watch_logfile()),
            summary=f"Background watcher running (pid {pid}); organizing new "
                    f"files in {len(folders)} folder(s) every {interval}s.",
        )

    if mode == "watch_stop":
        stopped = stop_watch_process()
        return tool_result(mode="watch_stop", stopped=stopped,
                           summary="Watcher stopped." if stopped else "No watcher was running.")

    if mode == "status":
        pid = watcher_running()
        manifest = _default_manifest_path()
        moves_logged = 0
        if manifest.exists():
            try:
                moves_logged = sum(1 for ln in manifest.read_text(
                    encoding="utf-8").splitlines() if ln.strip())
            except OSError:
                pass
        return tool_result(
            mode="status", watcher_running=bool(pid), pid=pid,
            default_folders=[str(f) for f in default_target_folders()],
            moves_in_manifest=moves_logged, manifest=str(manifest),
        )

    if mode == "undo":
        res = undo(_default_manifest_path())
        return tool_result(mode="undo", restored=len(res.restored),
                           errors=len(res.errors),
                           summary=f"Restored {len(res.restored)} file(s) to their "
                                   "original locations.")

    return tool_error(
        f"Unknown mode '{mode}'. Use one of: preview, organize, watch_start, "
        "watch_stop, status, undo."
    )


ORGANIZE_FILES_SCHEMA = {
    "name": "organize_files",
    "description": (
        "Automatically organize the user's folders (Downloads, Desktop, Documents, "
        "Pictures by default) into category subfolders — Images/, PDFs/, Documents/, "
        "Spreadsheets/, Archives/, Audio/, Video/, Code/, Installers/, Screenshots/, "
        "Other/. SAFE: never deletes, never overwrites (collision-safe rename), skips "
        "files still downloading and hidden/system files, idempotent, and every move is "
        "logged so it can be undone.\n\n"
        "Modes:\n"
        "  preview      — show what WOULD move, touching nothing (default; do this first).\n"
        "  organize     — perform the moves once and record an undo manifest.\n"
        "  watch_start  — start a background watcher that tidies new files in real time.\n"
        "  watch_stop   — stop the background watcher.\n"
        "  status       — report whether the watcher is running and recent activity.\n"
        "  undo         — reverse the most recent organize run.\n\n"
        "Prefer 'preview' before 'organize' so the user can see the plan. Omit 'folders' "
        "to use the sensible defaults."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "mode": {
                "type": "string",
                "enum": ["preview", "organize", "watch_start", "watch_stop", "status", "undo"],
                "description": "What to do. Default 'preview' (safe, moves nothing).",
                "default": "preview",
            },
            "folders": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Folders to organize (absolute or ~/ paths). Omit to use "
                               "the defaults: Downloads, Desktop, Documents, Pictures.",
            },
            "interval": {
                "type": "number",
                "description": "watch_start only: seconds between scans (default 5).",
                "default": DEFAULT_WATCH_INTERVAL_SECONDS,
            },
        },
        "required": [],
    },
}


def _handle_organize_files(args, **kw):
    return organize_files_tool(args or {})


registry.register(
    name="organize_files",
    toolset="file",
    schema=ORGANIZE_FILES_SCHEMA,
    handler=_handle_organize_files,
    check_fn=_check_file_reqs,
    emoji="🗂️",
    max_result_size_chars=50_000,
)


# ---------------------------------------------------------------------------
# CLI / daemon entry point
# ---------------------------------------------------------------------------

def _print_result(res: OrganizeResult) -> None:
    print(res.summary())
    for src, dst in res.moved:
        arrow = "would move" if res.dry_run else "moved"
        print(f"  {arrow}: {src.name} → {dst.parent.name}/")
    for path, reason in res.errors:
        print(f"  ERROR {path}: {reason}")


def main(argv=None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="xavani-organize",
        description="Xavani automatic file organizer — safe, reversible, cross-platform.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_prev = sub.add_parser("preview", help="show what would move (touches nothing)")
    p_prev.add_argument("folders", nargs="*", help="folders (default: the standard set)")

    p_org = sub.add_parser("organize", help="organize once (records an undo manifest)")
    p_org.add_argument("folders", nargs="*")
    p_org.add_argument("--yes", action="store_true", help="skip the confirmation prompt")

    p_watch = sub.add_parser("watch", help="run the real-time watcher in the foreground")
    p_watch.add_argument("--folders", nargs="*")
    p_watch.add_argument("--interval", type=float, default=DEFAULT_WATCH_INTERVAL_SECONDS)

    sub.add_parser("undo", help="reverse the most recent organize run")
    sub.add_parser("status", help="show watcher status and defaults")

    p_inst = sub.add_parser("install-autostart", help="run the watcher automatically at login")
    p_inst.add_argument("--folders", nargs="*")
    p_inst.add_argument("--interval", type=float, default=DEFAULT_WATCH_INTERVAL_SECONDS)
    sub.add_parser("uninstall-autostart", help="remove the login auto-start entry")

    args = parser.parse_args(argv)
    folders = [Path(f).expanduser() for f in (getattr(args, "folders", None) or [])] \
        or default_target_folders()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.cmd == "preview":
        _print_result(organize_folders(folders, dry_run=True))
        return 0

    if args.cmd == "organize":
        preview = organize_folders(folders, dry_run=True)
        if not preview.moved:
            print("Nothing to organize.")
            return 0
        _print_result(preview)
        if not args.yes:
            reply = input(f"\nMove {len(preview.moved)} file(s)? [y/N] ").strip().lower()
            if reply not in ("y", "yes"):
                print("Aborted.")
                return 1
        res = organize_folders(folders, dry_run=False, manifest_path=_default_manifest_path())
        print()
        _print_result(res)
        print("\nUndo with:  python -m tools.file_organizer undo")
        return 0

    if args.cmd == "watch":
        watch(folders, interval=args.interval, log=lambda m, *a: print(m % a if a else m))
        return 0

    if args.cmd == "undo":
        res = undo(_default_manifest_path())
        print(f"Restored {len(res.restored)} file(s).")
        for _dst, final in res.restored:
            print(f"  → {final}")
        return 0

    if args.cmd == "status":
        pid = watcher_running()
        print(f"Watcher: {'running (pid %d)' % pid if pid else 'not running'}")
        print("Default folders:")
        for f in default_target_folders():
            print(f"  {f}")
        return 0

    if args.cmd == "install-autostart":
        print(install_autostart(folders=folders, interval=args.interval))
        return 0

    if args.cmd == "uninstall-autostart":
        print(uninstall_autostart())
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
