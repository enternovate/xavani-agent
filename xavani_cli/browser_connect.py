# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Shared helpers for attaching Xavani to a local Chrome CDP port."""

from __future__ import annotations

import os
import platform
import shlex
import shutil
import subprocess

from xavani_constants import get_xavani_home


DEFAULT_BROWSER_CDP_PORT = 9222
DEFAULT_BROWSER_CDP_URL = f"http://127.0.0.1:{DEFAULT_BROWSER_CDP_PORT}"

_DARWIN_APPS = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
)

_WINDOWS_INSTALL_PARTS = (
    ("Google", "Chrome", "Application", "chrome.exe"),
    ("Chromium", "Application", "chrome.exe"),
    ("Chromium", "Application", "chromium.exe"),
    ("BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
    ("Microsoft", "Edge", "Application", "msedge.exe"),
)

_LINUX_BIN_NAMES = (
    "google-chrome", "google-chrome-stable", "chromium-browser",
    "chromium", "brave-browser", "microsoft-edge",
)

_WINDOWS_BIN_NAMES = (
    "chrome.exe", "msedge.exe", "brave.exe", "chromium.exe",
    "chrome", "msedge", "brave", "chromium",
)


def get_chrome_debug_candidates(system: str) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()

    def add(path: str | None) -> None:
        if not path:
            return
        normalized = os.path.normcase(os.path.normpath(path))
        if normalized in seen or not os.path.isfile(path):
            return
        candidates.append(path)
        seen.add(normalized)

    def add_install_paths(bases: tuple[str | None, ...]) -> None:
        for base in filter(None, bases):
            for parts in _WINDOWS_INSTALL_PARTS:
                add(os.path.join(base, *parts))

    if system == "Darwin":
        for app in _DARWIN_APPS:
            add(app)
        return candidates

    if system == "Windows":
        for name in _WINDOWS_BIN_NAMES:
            add(shutil.which(name))
        add_install_paths((
            os.environ.get("ProgramFiles"),
            os.environ.get("ProgramFiles(x86)"),
            os.environ.get("LOCALAPPDATA"),
        ))
        return candidates

    for name in _LINUX_BIN_NAMES:
        add(shutil.which(name))
    add_install_paths(("/mnt/c/Program Files", "/mnt/c/Program Files (x86)"))
    return candidates


def chrome_debug_data_dir() -> str:
    return str(get_xavani_home() / "chrome-debug")


def _chrome_debug_args(port: int) -> list[str]:
    return [
        f"--remote-debugging-port={port}",
        f"--user-data-dir={chrome_debug_data_dir()}",
        "--no-first-run",
        "--no-default-browser-check",
    ]


def manual_chrome_debug_command(port: int = DEFAULT_BROWSER_CDP_PORT, system: str | None = None) -> str | None:
    system = system or platform.system()
    candidates = get_chrome_debug_candidates(system)

    if candidates:
        argv = [candidates[0], *_chrome_debug_args(port)]
        return subprocess.list2cmdline(argv) if system == "Windows" else shlex.join(argv)

    if system == "Darwin":
        data_dir = chrome_debug_data_dir()
        return (
            f'open -a "Google Chrome" --args --remote-debugging-port={port} '
            f'--user-data-dir="{data_dir}" --no-first-run --no-default-browser-check'
        )

    return None


def _detach_kwargs(system: str) -> dict:
    if system != "Windows":
        return {"start_new_session": True}
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
        subprocess, "CREATE_NEW_PROCESS_GROUP", 0
    )
    return {"creationflags": flags} if flags else {}


def try_launch_chrome_debug(port: int = DEFAULT_BROWSER_CDP_PORT, system: str | None = None) -> bool:
    system = system or platform.system()
    candidates = get_chrome_debug_candidates(system)
    if not candidates:
        return False

    os.makedirs(chrome_debug_data_dir(), exist_ok=True)
    try:
        subprocess.Popen(
            [candidates[0], *_chrome_debug_args(port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **_detach_kwargs(system),
        )
        return True
    except Exception:
        return False


_LOOPBACK_PROBE_HOSTS = ("127.0.0.1", "[::1]")
_LOOPBACK_SOCKET_HOSTS = ("127.0.0.1", "::1")


def is_browser_debug_ready(url: str, timeout: float = 1.0) -> bool:
    import socket
    import urllib.request
    from urllib.parse import urlparse

    parsed = urlparse(url if "://" in url else f"http://{url}")
    try:
        port = parsed.port or (443 if parsed.scheme in {"https", "wss"} else 80)
    except ValueError:
        return False

    if parsed.scheme in {"ws", "wss"} and parsed.path.startswith("/devtools/browser/"):
        if not parsed.hostname:
            return False
        try:
            with socket.create_connection((parsed.hostname, port), timeout=timeout):
                return True
        except OSError:
            return False

    scheme = {"ws": "http", "wss": "https"}.get(parsed.scheme, parsed.scheme)
    if scheme not in {"http", "https"} or not parsed.netloc:
        return False

    root = f"{scheme}://{parsed.netloc}".rstrip("/")
    for probe in (f"{root}/json/version", f"{root}/json"):
        try:
            with urllib.request.urlopen(probe, timeout=timeout) as resp:
                if 200 <= getattr(resp, "status", 200) < 300:
                    return True
        except Exception:
            continue
    return False


def discover_local_cdp_url(port: int, timeout: float = 1.0) -> str | None:
    for host in _LOOPBACK_PROBE_HOSTS:
        url = f"http://{host}:{port}"
        if is_browser_debug_ready(url, timeout=timeout):
            return url
    return None


def local_port_in_use(port: int, timeout: float = 0.5) -> bool:
    import socket

    for host in _LOOPBACK_SOCKET_HOSTS:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            continue
    return False


def find_free_debug_port(preferred: int = DEFAULT_BROWSER_CDP_PORT, attempts: int = 10) -> int:
    import socket

    for port in range(preferred + 1, preferred + 1 + attempts):
        bindable = True
        for family, host in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
            try:
                with socket.socket(family, socket.SOCK_STREAM) as sock:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sock.bind((host, port))
            except OSError:
                bindable = False
                break
        if bindable:
            return port
    return preferred + 1
