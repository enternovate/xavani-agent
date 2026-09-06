# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Shared constants for Xavani Agent.

Import-safe module with no dependencies — can be imported from anywhere
without risk of circular imports.
"""

import os
import sys
import sysconfig
from contextvars import ContextVar, Token
from pathlib import Path


_profile_fallback_warned: bool = False
_UNSET = object()
_XAVANI_HOME_OVERRIDE: ContextVar[str | object] = ContextVar(
    "_XAVANI_HOME_OVERRIDE", default=_UNSET
)


def set_xavani_home_override(path: str | Path | None) -> Token:
    """Set a context-local Xavani home override and return its reset token.

    This is for in-process, per-task scoping.  It deliberately does not mutate
    ``os.environ`` because that is shared by every thread in the process.
    """
    value: str | object = _UNSET if path is None else str(path)
    return _XAVANI_HOME_OVERRIDE.set(value)


def reset_xavani_home_override(token: Token) -> None:
    """Restore the previous context-local Xavani home override."""
    _XAVANI_HOME_OVERRIDE.reset(token)


def get_xavani_home_override() -> str | None:
    """Return the active context-local Xavani home override, if any."""
    override = _XAVANI_HOME_OVERRIDE.get()
    if override is _UNSET or not override:
        return None
    return str(override)


def get_xavani_home() -> Path:
    """Return the Xavani home directory (default: ~/.xavani).

    Reads XAVANI_HOME env var, falls back to ~/.xavani.
    This is the single source of truth — all other copies should import this.

    When ``XAVANI_HOME`` is unset but an ``active_profile`` file indicates
    a non-default profile is active, logs a loud one-shot warning to
    ``errors.log`` so cross-profile data corruption is diagnosable instead
    of silent.  Behavior is unchanged otherwise — we still return
    ``~/.xavani`` — because raising here would brick 30+ module-level
    callers that import this at load time.  Subprocess spawners are
    expected to propagate ``XAVANI_HOME`` explicitly (see the systemd
    template in ``xavani_cli/gateway.py`` and the kanban dispatcher in
    ``xavani_cli/kanban_db.py``).  See https://github.com/enternovate/xavani-agent/issues/18594.
    """
    override = get_xavani_home_override()
    if override:
        return Path(override)

    val = os.environ.get("XAVANI_HOME", "").strip()
    if val:
        return Path(val)

    # Guard: if a non-default profile is sticky-active, warn once that
    # the fallback to the default profile is almost certainly wrong.
    global _profile_fallback_warned
    if not _profile_fallback_warned:
        try:
            # Inline the default-root resolution from get_default_xavani_root()
            # to stay import-safe (this function is called from module scope
            # in 30+ files; we cannot afford to trigger logging setup here).
            active_path = (Path.home() / ".xavani" / "active_profile")
            active = active_path.read_text().strip() if active_path.exists() else ""
        except (UnicodeDecodeError, OSError):
            active = ""
        if active and active != "default":
            _profile_fallback_warned = True
            # Write directly to stderr.  We intentionally do NOT route this
            # through ``logging`` because (a) this function is called at
            # module-import time from 30+ sites, often before logging is
            # configured, and (b) root-logger propagation would double-emit
            # on consoles where a StreamHandler is already attached.
            import sys
            msg = (
                f"[XAVANI_HOME fallback] XAVANI_HOME is unset but active "
                f"profile is {active!r}. Falling back to ~/.xavani, which "
                f"is the DEFAULT profile — not {active!r}. Any data this "
                f"process writes will land in the wrong profile. The "
                f"subprocess spawner should pass XAVANI_HOME explicitly "
                f"(see issue #18594)."
            )
            try:
                sys.stderr.write(msg + "\n")
                sys.stderr.flush()
            except Exception:
                pass

    return Path.home() / ".xavani"


def get_process_xavani_home() -> Path:
    """Return the Xavani home for the running process, ignoring task overrides.

    Unlike :func:`get_xavani_home`, this never follows the context-local
    override set by :func:`set_xavani_home_override`. It resolves only the
    process ``XAVANI_HOME`` env var (falling back to the platform default),
    so it reflects the scope the process was launched under **as long as
    nothing mutates ``os.environ`` in-process**.

    Use this for machine/process-level assets that live under the launch
    home and must stay visible even while a request is scoped to another
    profile. Do NOT use it for genuinely profile-scoped data (memories,
    backups, checkpoints, provider config) — those should keep following
    the override.
    """
    val = os.environ.get("XAVANI_HOME", "").strip()
    if val:
        return Path(val)
    return Path.home() / ".xavani"


def get_default_xavani_root() -> Path:
    """Return the root Xavani directory for profile-level operations.

    In standard deployments this is ``~/.xavani``.

    In Docker or custom deployments where ``XAVANI_HOME`` points outside
    ``~/.xavani`` (e.g. ``/opt/data``), returns ``XAVANI_HOME`` directly
    — that IS the root.

    In profile mode where ``XAVANI_HOME`` is ``<root>/profiles/<name>``,
    returns ``<root>`` so that ``profile list`` can see all profiles.
    Works both for standard (``~/.xavani/profiles/coder``) and Docker
    (``/opt/data/profiles/coder``) layouts.

    Import-safe — no dependencies beyond stdlib.
    """
    native_home = Path.home() / ".xavani"
    env_home = os.environ.get("XAVANI_HOME", "")
    if not env_home:
        return native_home
    env_path = Path(env_home)
    try:
        env_path.resolve().relative_to(native_home.resolve())
        # XAVANI_HOME is under ~/.xavani (normal or profile mode)
        return native_home
    except ValueError:
        pass

    # Docker / custom deployment.
    # Check if this is a profile path: <root>/profiles/<name>
    # If the immediate parent dir is named "profiles", the root is
    # the grandparent — this covers Docker profiles correctly.
    if env_path.parent.name == "profiles":
        return env_path.parent.parent

    # Not a profile path — XAVANI_HOME itself is the root
    return env_path


def _get_packaged_data_dir(name: str) -> Path | None:
    """Return an installed data-files directory if one exists.

    Used to discover bundled skills/optional-skills when Xavani is installed
    from a wheel that emitted them via setuptools data_files.
    """
    candidates = []
    for scheme in ("data", "purelib", "platlib"):
        raw = sysconfig.get_path(scheme)
        if raw:
            candidates.append(Path(raw) / name)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def get_optional_skills_dir(default: Path | None = None) -> Path:
    """Return the optional-skills directory, honoring package-manager wrappers.

    Packaged installs may ship ``optional-skills`` outside the Python package
    tree and expose it via ``XAVANI_OPTIONAL_SKILLS``.
    """
    override = os.getenv("XAVANI_OPTIONAL_SKILLS", "").strip()
    if override:
        return Path(override)
    packaged = _get_packaged_data_dir("optional-skills")
    if packaged is not None:
        return packaged
    if default is not None:
        return default
    return get_xavani_home() / "optional-skills"


def get_optional_mcps_dir(default: Path | None = None) -> Path:
    """Return the optional-mcps directory, honoring package-manager wrappers.

    Packaged installs may ship ``optional-mcps`` outside the Python package
    tree and expose it via ``XAVANI_OPTIONAL_MCPS``.
    """
    override = os.getenv("XAVANI_OPTIONAL_MCPS", "").strip()
    if override:
        return Path(override)
    packaged = _get_packaged_data_dir("optional-mcps")
    if packaged is not None:
        return packaged
    if default is not None:
        return default
    return get_xavani_home() / "optional-mcps"


def get_bundled_skills_dir(default: Path | None = None) -> Path:
    """Return the bundled skills directory for source and packaged installs.

    Resolution order:
        1. ``XAVANI_BUNDLED_SKILLS`` env var (Nix wrapper / explicit override)
        2. Wheel-installed ``<sysconfig data>/skills`` (pip install path)
        3. Caller-supplied ``default`` (typically the source-checkout path)
        4. ``<XAVANI_HOME>/skills`` last-resort
    """
    override = os.getenv("XAVANI_BUNDLED_SKILLS", "").strip()
    if override:
        return Path(override)
    packaged = _get_packaged_data_dir("skills")
    if packaged is not None:
        return packaged
    if default is not None:
        return default
    return get_xavani_home() / "skills"


def get_xavani_dir(new_subpath: str, old_name: str) -> Path:
    """Resolve a Xavani subdirectory with backward compatibility.

    New installs get the consolidated layout (e.g. ``cache/images``).
    Existing installs that already have the old path (e.g. ``image_cache``)
    keep using it — no migration required.

    Args:
        new_subpath: Preferred path relative to XAVANI_HOME (e.g. ``"cache/images"``).
        old_name: Legacy path relative to XAVANI_HOME (e.g. ``"image_cache"``).

    Returns:
        Absolute ``Path`` — old location if it exists on disk, otherwise the new one.
    """
    home = get_xavani_home()
    old_path = home / old_name
    if old_path.exists():
        return old_path
    return home / new_subpath


def display_xavani_home() -> str:
    """Return a user-friendly display string for the current XAVANI_HOME.

    Uses ``~/`` shorthand for readability::

        default:  ``~/.xavani``
        profile:  ``~/.xavani/profiles/coder``
        custom:   ``/opt/xavani-custom``

    Use this in **user-facing** print/log messages instead of hardcoding
    ``~/.xavani``.  For code that needs a real ``Path``, use
    :func:`get_xavani_home` instead.
    """
    home = get_xavani_home()
    try:
        return "~/" + str(home.relative_to(Path.home()))
    except ValueError:
        return str(home)


def get_subprocess_home() -> str | None:
    """Return a per-profile HOME directory for subprocesses, or None.

    When ``{XAVANI_HOME}/home/`` exists on disk, subprocesses should use it
    as ``HOME`` so system tools (git, ssh, gh, npm …) write their configs
    inside the Xavani data directory instead of the OS-level ``/root`` or
    ``~/``.  This provides:

    * **Docker persistence** — tool configs land inside the persistent volume.
    * **Profile isolation** — each profile gets its own git identity, SSH
      keys, gh tokens, etc.

    The Python process's own ``os.environ["HOME"]`` and ``Path.home()`` are
    **never** modified — only subprocess environments should inject this value.
    Activation is directory-based: if the ``home/`` subdirectory doesn't
    exist, returns ``None`` and behavior is unchanged.
    """
    xavani_home = get_xavani_home_override() or os.getenv("XAVANI_HOME")
    if not xavani_home:
        return None
    profile_home = os.path.join(xavani_home, "home")
    if os.path.isdir(profile_home):
        return profile_home
    return None


VALID_REASONING_EFFORTS = ("minimal", "low", "medium", "high", "xhigh")


def parse_reasoning_effort(effort: str) -> dict | None:
    """Parse a reasoning effort level into a config dict.

    Valid levels: "none", "minimal", "low", "medium", "high", "xhigh".
    Returns None when the input is empty or unrecognized (caller uses default).
    Returns {"enabled": False} for "none".
    Returns {"enabled": True, "effort": <level>} for valid effort levels.
    """
    if not effort or not effort.strip():
        return None
    effort = effort.strip().lower()
    if effort == "none":
        return {"enabled": False}
    if effort in VALID_REASONING_EFFORTS:
        return {"enabled": True, "effort": effort}
    return None


def is_termux() -> bool:
    """Return True when running inside a Termux (Android) environment.

    Checks ``TERMUX_VERSION`` (set by Termux) or the Termux-specific
    ``PREFIX`` path.  Import-safe — no heavy deps.
    """
    prefix = os.getenv("PREFIX", "")
    return bool(os.getenv("TERMUX_VERSION") or "com.termux/files/usr" in prefix)


_wsl_detected: bool | None = None


def is_wsl() -> bool:
    """Return True when running inside WSL (Windows Subsystem for Linux).

    Checks ``/proc/version`` for the ``microsoft`` marker that both WSL1
    and WSL2 inject.  Result is cached for the process lifetime.
    Import-safe — no heavy deps.
    """
    global _wsl_detected
    if _wsl_detected is not None:
        return _wsl_detected
    try:
        with open("/proc/version", "r", encoding="utf-8") as f:
            _wsl_detected = "microsoft" in f.read().lower()
    except Exception:
        _wsl_detected = False
    return _wsl_detected


_container_detected: bool | None = None


def is_container() -> bool:
    """Return True when running inside a Docker/Podman container.

    Checks ``/.dockerenv`` (Docker), ``/run/.containerenv`` (Podman),
    and ``/proc/1/cgroup`` for container runtime markers.  Result is
    cached for the process lifetime.  Import-safe — no heavy deps.
    """
    global _container_detected
    if _container_detected is not None:
        return _container_detected
    if os.path.exists("/.dockerenv"):
        _container_detected = True
        return True
    if os.path.exists("/run/.containerenv"):
        _container_detected = True
        return True
    try:
        with open("/proc/1/cgroup", "r", encoding="utf-8") as f:
            cgroup = f.read()
            if "docker" in cgroup or "podman" in cgroup or "/lxc/" in cgroup:
                _container_detected = True
                return True
    except OSError:
        pass
    _container_detected = False
    return False


# ─── Well-Known Paths ─────────────────────────────────────────────────────────


def get_config_path() -> Path:
    """Return the path to ``config.yaml`` under XAVANI_HOME.

    Replaces the ``get_xavani_home() / "config.yaml"`` pattern repeated
    in 7+ files (skill_utils.py, xavani_logging.py, xavani_time.py, etc.).
    """
    return get_xavani_home() / "config.yaml"


def get_skills_dir() -> Path:
    """Return the path to the skills directory under XAVANI_HOME."""
    return get_xavani_home() / "skills"



def get_env_path() -> Path:
    """Return the path to the ``.env`` file under XAVANI_HOME."""
    return get_xavani_home() / ".env"


# ─── Network Preferences ─────────────────────────────────────────────────────


def apply_ipv4_preference(force: bool = False) -> None:
    """Monkey-patch ``socket.getaddrinfo`` to prefer IPv4 connections.

    On servers with broken or unreachable IPv6, Python tries AAAA records
    first and hangs for the full TCP timeout before falling back to IPv4.
    This affects httpx, requests, urllib, the OpenAI SDK — everything that
    uses ``socket.getaddrinfo``.

    When *force* is True, patches ``getaddrinfo`` so that calls with
    ``family=AF_UNSPEC`` (the default) resolve as ``AF_INET`` instead,
    skipping IPv6 entirely.  If no A record exists, falls back to the
    original unfiltered resolution so pure-IPv6 hosts still work.

    Safe to call multiple times — only patches once.
    Set ``network.force_ipv4: true`` in ``config.yaml`` to enable.
    """
    if not force:
        return

    import socket

    # Guard against double-patching
    if getattr(socket.getaddrinfo, "_xavani_ipv4_patched", False):
        return

    _original_getaddrinfo = socket.getaddrinfo

    def _ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        if family == 0:  # AF_UNSPEC — caller didn't request a specific family
            try:
                return _original_getaddrinfo(
                    host, port, socket.AF_INET, type, proto, flags
                )
            except socket.gaierror:
                # No A record — fall back to full resolution (pure-IPv6 hosts)
                return _original_getaddrinfo(host, port, family, type, proto, flags)
        return _original_getaddrinfo(host, port, family, type, proto, flags)

    _ipv4_getaddrinfo._xavani_ipv4_patched = True  # type: ignore[attr-defined]
    socket.getaddrinfo = _ipv4_getaddrinfo  # type: ignore[assignment]


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODELS_URL = f"{OPENROUTER_BASE_URL}/models"

AI_GATEWAY_BASE_URL = "https://ai-gateway.vercel.sh/v1"


def venv_bin_dir(venv_dir, *, windows: bool | None = None) -> Path:
    if windows is None:
        windows = sys.platform == "win32"
    return Path(venv_dir) / ("Scripts" if windows else "bin")


def project_venv_dir(project_root) -> Path | None:
    for name in ("venv", ".venv"):
        candidate = Path(project_root) / name
        if candidate.is_dir():
            return candidate
    return None


def venv_python_path(venv_dir, *, windows: bool | None = None) -> Path:
    """Path to the Python interpreter inside *venv_dir* (may not exist)."""
    if windows is None:
        windows = sys.platform == "win32"
    return venv_bin_dir(venv_dir, windows=windows) / (
        "python.exe" if windows else "python"
    )


def iter_xavani_node_dirs(home: Path | None = None) -> list[Path]:
    """Return Xavani-managed Node.js directories in preferred lookup order.

    Windows installs from ``scripts/install.ps1`` unpack portable Node directly
    into ``%LOCALAPPDATA%\\\\xavani\\\\node``. POSIX installs use
    ``$XAVANI_HOME/node/bin``. Include both shapes on every platform so mixed
    or migrated installs still work.
    """
    root = home or get_xavani_home()
    dirs = [root / "node"]
    bin_dir = root / "node" / "bin"
    # NOTE: keep this ordering in sync with hermesManagedNodePathEntries() in
    # apps/desktop/electron/backend-env.ts — the Electron main process is Node
    # and cannot import this module, so the platform-ordering rule is mirrored
    # there (once; main.ts imports it rather than keeping its own copy).
    if sys.platform == "win32":
        return dirs + [bin_dir]
    return [bin_dir] + dirs


def with_xavani_node_path(env: dict[str, str] | None = None) -> dict[str, str]:
    """Return *env* with Xavani-managed Node directories prepended to PATH."""
    merged = dict(os.environ if env is None else env)
    existing = merged.get("PATH", "")
    parts = [p for p in existing.split(os.pathsep) if p]
    managed = [str(path) for path in iter_xavani_node_dirs() if path.is_dir()]
    for entry in reversed(managed):
        if entry not in parts:
            parts.insert(0, entry)
    merged["PATH"] = os.pathsep.join(parts)
    return merged


# ─── Partial-update diagnostics ──────────────────────────────────────────────

# Top-level packages/modules that ship as part of Xavani itself. An ImportError
# naming one of these means our own tree is inconsistent; anything else is a
# third-party problem with different remediation. Single source of truth —
# `xavani_cli.update_cmd`'s post-update probe consumes this same set so the
# guard that BLOCKS and the hint that EXPLAINS can never disagree.
FIRST_PARTY_MODULE_ROOTS = frozenset(
    {
        "agent",
        "acp_adapter",
        "cli",
        "cron",
        "gateway",
        "model_tools",
        "plugins",
        "providers",
        "tools",
        "toolsets",
        "run_agent",
        "tui_gateway",
        "utils",
        "xavani_cli",
        "xavani_constants",
        "xavani_state",
    }
)


def is_first_party_module(name: str | None) -> bool:
    """True when *name* is a module that ships with Xavani.

    Matches on the first dotted segment against an exact set — a substring or
    ``startswith`` test would also claim third-party ``agents``, ``agentops``,
    and ``toolsets_x``.
    """
    root = str(name).split(".")[0] if name else ""
    if not root:
        return False
    return root in FIRST_PARTY_MODULE_ROOTS or root.startswith("xavani_")


def partial_update_hint(exc: BaseException) -> list[str]:
    """Return recovery guidance lines when *exc* looks like a half-updated tree.

    An interrupted or partially-applied update can leave the checkout with new
    files in one package and stale files in another. Every file still parses,
    so nothing is corrupt in the usual sense — but a module that imports a name
    added in the same release from a sibling that wasn't refreshed dies with
    ``ImportError: cannot import name 'X' from 'y'`` on every startup.

    Users hit this as an opaque crash with no indication that the *install*,
    rather than their config, is the problem — and `xavani update` is exactly
    the command they need but are least likely to trust after a failed update.
    Return the guidance so callers can print it alongside the raw error.

    Returns an empty list for unrelated exceptions, so callers can splat it
    unconditionally.
    """
    if not isinstance(exc, ImportError):
        return []
    # A missing third-party dependency is a different problem (bad venv, missing
    # extra) with different remediation, so don't claim a partial update.
    if isinstance(exc, ModuleNotFoundError):
        return []
    name = getattr(exc, "name", None)
    if not is_first_party_module(name):
        return []
    return [
        "",
        "This looks like a partially-updated install: one module was refreshed "
        "and a related one was not.",
        "Re-run the update to bring the whole tree to the same version:",
        "    xavani update",
        "If that also fails, reinstall: https://enternovate.co.za/xavani-agent",
    ]


def emit_partial_update_hint(exc: BaseException, *, file=None) -> bool:
    """Print recovery guidance for a half-updated tree.

    Returns True when guidance was written (caller should then exit), False
    when *exc* is not a first-party ``ImportError`` (caller should re-raise).
    """
    lines = partial_update_hint(exc)
    if not lines:
        return False
    out = sys.stderr if file is None else file
    print(f"Error: {exc}", file=out)
    for line in lines:
        print(line, file=out)
    return True


_DELETED_PROFILES_DIR = ".deleted"


def profile_tombstone_path(profile_home: Path) -> Path:
    return profile_home.parent / _DELETED_PROFILES_DIR / profile_home.name


def named_profile_is_deleted(profile_home: str | Path) -> bool:
    return profile_tombstone_path(Path(profile_home)).exists()


def mark_named_profile_deleted(profile_home: str | Path) -> None:
    marker = profile_tombstone_path(Path(profile_home))
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("deleted\n", encoding="utf-8")


def clear_named_profile_deleted(profile_home: str | Path) -> None:
    profile_tombstone_path(Path(profile_home)).unlink(missing_ok=True)
